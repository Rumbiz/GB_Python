import sqlite3
import re

def create_database(db_path):
    """Создает или подключается к базе данных SQLite и создает таблицы contacts и phone_numbers."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_name TEXT,
                first_name TEXT,
                middle_name TEXT,
                email TEXT,
                dob TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phone_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                phone_number TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
        """)
    except sqlite3.OperationalError as e:
        print(f"Ошибка при создании базы данных: {e}")
        conn.close()
        return None
    conn.commit()
    return conn

def load_contacts(conn):
    """Загружает контакты и связанные с ними номера телефонов из базы данных SQLite."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT c.last_name, c.first_name, c.middle_name, c.email, c.dob, group_concat(pn.phone_number, ',') FROM contacts c LEFT JOIN phone_numbers pn ON c.id = pn.contact_id GROUP BY c.id")
    except sqlite3.OperationalError as e:
        print(f"Ошибка при загрузке контактов: {e}")
        return []
    contacts = []
    for last_name, first_name, middle_name, email, dob, phone_numbers in cursor.fetchall():
        name = ' '.join((last_name, first_name, middle_name)).strip()
        phones = [phone.strip() for phone in phone_numbers.split(',')] if phone_numbers else []
        contacts.append({'name': name, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name, 'email': email, 'dob': dob, 'phones': phones})
    return contacts

def validate_phone_number(phone_number):
    """Проверяет правильность формата номера телефона."""
    pattern = r'^\+?[\d\s\-\(\)]+$'
    return bool(re.match(pattern, phone_number))

def validate_email(email):
    """Проверяет правильность формата email."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_date(date):
    """Проверяет правильность формата даты рождения (dd.mm.yyyy)."""
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    return bool(re.match(pattern, date))

def save_contact(conn, last_name, first_name, middle_name, phones, email=None, dob=None):
    """Сохраняет контакт и связанные с ним номера телефонов в базе данных SQLite."""
    name = ' '.join((last_name, first_name, middle_name)).strip()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM contacts WHERE last_name = ? AND first_name = ? AND middle_name = ?", (last_name, first_name, middle_name))
    existing_contact = cursor.fetchone()

    # Проверка номеров телефонов
    valid_phones = [phone for phone in phones if validate_phone_number(phone)]
    if not valid_phones:
        print("Некорректный формат номера телефона. Контакт не сохранен.")
        return

    # Проверка email (если указан)
    if email and not validate_email(email):
        print("Некорректный формат email. Контакт не сохранен.")
        return

    # Проверка даты рождения (если указана)
    if dob and not validate_date(dob):
        print("Некорректный формат даты рождения. Контакт не сохранен.")
        return

    if existing_contact:
        contact_id = existing_contact[0]
        new_phones = [phone for phone in valid_phones if phone not in get_phone_numbers(conn, contact_id)]
        for phone in new_phones:
            cursor.execute("INSERT INTO phone_numbers (contact_id, phone_number) VALUES (?, ?)", (contact_id, phone))
        conn.commit()
        print(f"Новые номера телефонов добавлены к существующему контакту '{name}'.")
    else:
        cursor.execute("INSERT INTO contacts (last_name, first_name, middle_name, email, dob) VALUES (?, ?, ?, ?, ?)", (last_name, first_name, middle_name, email, dob))
        contact_id = cursor.lastrowid
        for phone in valid_phones:
            cursor.execute("INSERT INTO phone_numbers (contact_id, phone_number) VALUES (?, ?)", (contact_id, phone))
        conn.commit()
        print("Контакт добавлен.")

def edit_contact(conn, identifier, new_last_name=None, new_first_name=None, new_middle_name=None, new_phones=None, new_email=None, new_dob=None):
    """
    Редактирует контакт с заданным именем, фамилией, отчеством, номером телефона, email или датой рождения,
    заменяя его новыми данными.
    """
    cursor = conn.cursor()
    update_query = "UPDATE contacts SET "
    update_values = []
    if new_last_name:
        update_query += "last_name = ?, "
        update_values.append(new_last_name)
    if new_first_name:
        update_query += "first_name = ?, "
        update_values.append(new_first_name)
    if new_middle_name:
        update_query += "middle_name = ?, "
        update_values.append(new_middle_name)
    if new_email is not None:
        update_query += "email = ?, "
        update_values.append(new_email)
    if new_dob is not None:
        update_query += "dob = ?, "
        update_values.append(new_dob)
    update_query = update_query.rstrip(", ") + " WHERE last_name = ? OR first_name = ? OR middle_name = ? OR email = ? OR dob = ?"
    update_values.extend([identifier] * 5)
    try:
        cursor.execute(update_query, update_values)
    except sqlite3.OperationalError as e:
        print(f"Ошибка при редактировании контакта: {e}")
        return
    if cursor.rowcount > 0:
        conn.commit()
        contact_id = cursor.lastrowid
        if new_phones:
            cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ?", (contact_id,))
            valid_phones = [phone for phone in new_phones if validate_phone_number(phone)]
            for phone in valid_phones:
                cursor.execute("INSERT INTO phone_numbers (contact_id, phone_number) VALUES (?, ?)", (contact_id, phone))
        conn.commit()
        print("Контакт отредактирован.")
        # Обновляем контакты после редактирования
        contacts = load_contacts(conn)
    else:
        print("Контакт не найден.")

def get_phone_numbers(conn, contact_id):
    """Возвращает список номеров телефонов для указанного контакта."""
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number FROM phone_numbers WHERE contact_id = ?", (contact_id,))
    phone_numbers = [row[0] for row in cursor.fetchall()]
    return phone_numbers

def display_contacts(contacts):
  """Выводит список контактов на экран."""
  if not contacts:
      print("Справочник пуст.")
  else:
      print("Контакты:")
      for contact in contacts:
          print(f"{contact['last_name']} {contact['first_name']} {contact['middle_name']}: {', '.join(contact['phones'])}", end='')
          if contact['email']:
              print(f" Email: {contact['email']}", end='')
          if contact['dob']:
              print(f" Дата рождения: {contact['dob']}", end='')
          print()

def search_contacts(conn, query):
  """Ищет контакты по имени, фамилии, отчеству, номеру телефона, email или дате рождения."""
  cursor = conn.cursor()
  try:
      cursor.execute("""
          SELECT c.last_name, c.first_name, c.middle_name, c.email, c.dob, group_concat(pn.phone_number, ',')
          FROM contacts c
          LEFT JOIN phone_numbers pn ON c.id = pn.contact_id
          WHERE c.last_name LIKE ? OR c.first_name LIKE ? OR c.middle_name LIKE ? OR c.email LIKE ? OR c.dob LIKE ? OR pn.phone_number LIKE ?
          GROUP BY c.id
      """, (f"%{query}%",) * 6)
  except sqlite3.OperationalError as e:
      print(f"Ошибка при поиске контактов: {e}")
      return []
  contacts = []
  for last_name, first_name, middle_name, email, dob, phone_numbers in cursor.fetchall():
      name = ' '.join((last_name, first_name, middle_name)).strip()
      phones = [phone.strip() for phone in phone_numbers.split(',')] if phone_numbers else []
      contacts.append({'name': name, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name, 'email': email, 'dob': dob, 'phones': phones})
  return contacts

def delete_phone_number(conn, contact_identifier):
    """Удаляет номер телефона для указанного контакта."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT c.id, c.last_name, c.first_name, c.middle_name, pn.phone_number
            FROM contacts c
            LEFT JOIN phone_numbers pn ON c.id = pn.contact_id
            WHERE (c.last_name LIKE ? OR c.first_name LIKE ? OR c.middle_name LIKE ? OR c.email LIKE ?)
        """, (f"%{contact_identifier}%",) * 4)
    except sqlite3.OperationalError as e:
        print(f"Ошибка при удалении номера телефона: {e}")
        return

    contact_info = cursor.fetchall()

    if not contact_info:
        print("Контакт не найден.")
        return

    if len(contact_info) == 1:
        contact_id, last_name, first_name, middle_name, phone_number = contact_info[0]
        print(f"Контакт: {last_name} {first_name} {middle_name}, Номер телефона: {phone_number}")
        confirm = input("Удалить этот номер телефона? (y/n) ").lower()
        if confirm == 'y':
            cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ? AND phone_number = ?", (contact_id, phone_number))
            conn.commit()
            print(f"Номер телефона {phone_number} удален из контакта.")
        else:
            print("Операция отменена.")
    else:
        print("Найдено несколько контактов. Выберите контакт:")
        for i, (contact_id, last_name, first_name, middle_name, phone_number) in enumerate(contact_info, start=1):
            print(f"{i}. {last_name} {first_name} {middle_name}, Номер телефона: {phone_number}")

        choice = input("Введите номер выбранного контакта: ")
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(contact_info):
                contact_id, last_name, first_name, middle_name, phone_number = contact_info[choice_index]
                print(f"Контакт: {last_name} {first_name} {middle_name}, Номер телефона: {phone_number}")
                confirm = input("Удалить этот номер телефона? (y/n) ").lower()
                if confirm == 'y':
                    cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ? AND phone_number = ?", (contact_id, phone_number))
                    conn.commit()
                    print(f"Номер телефона {phone_number} удален из контакта.")
                else:
                    print("Операция отменена.")
            else:
                print("Неверный выбор номера.")
        except ValueError:
            print("Неверный формат ввода.")

def delete_contact(conn, contact_identifier):
    """Удаляет контакт по имени, фамилии, отчеству, номеру телефона или email."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, last_name, first_name, middle_name
            FROM contacts
            WHERE last_name LIKE ? OR first_name LIKE ? OR middle_name LIKE ? OR email LIKE ?
        """, (f"%{contact_identifier}%",) * 4)
    except sqlite3.OperationalError as e:
        print(f"Ошибка при удалении контакта: {e}")
        return
    contact_info = cursor.fetchall()

    if not contact_info:
        print("Контакт не найден.")
        return

    if len(contact_info) == 1:
        contact_id, last_name, first_name, middle_name = contact_info[0]
        print(f"Контакт: {last_name} {first_name} {middle_name}")
        confirm = input("Удалить этот контакт? (y/n) ").lower()
        if confirm == 'y':
            cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ?", (contact_id,))
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            conn.commit()
            print("Контакт удален.")
        else:
            print("Операция отменена.")
    else:
        print("Найдено несколько контактов. Выберите контакт:")
        for i, (contact_id, last_name, first_name, middle_name) in enumerate(contact_info, start=1):
            print(f"{i}. {last_name} {first_name} {middle_name}")

        choice = input("Введите номер выбранного контакта: ")
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(contact_info):
                contact_id, last_name, first_name, middle_name = contact_info[choice_index]
                print(f"Контакт: {last_name} {first_name} {middle_name}")
                confirm = input("Удалить этот контакт? (y/n) ").lower()
                if confirm == 'y':
                    cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ?", (contact_id,))
                    cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
                    conn.commit()
                    print("Контакт удален.")
                else:
                    print("Операция отменена.")
            else:
                print("Неверный выбор номера.")
        except ValueError:
            print("Неверный формат ввода.")

def get_database_path():
  """Получает от пользователя путь к файлу базы данных."""
  return input("Введите имя файла базы данных, или Enter для значения по умолчанию").strip() or "contacts.db"

def get_contact_details():
  """Получает от пользователя детали нового контакта."""
  last_name = input("Введите фамилию: ")
  first_name = input("Введите имя: ")
  middle_name = input("Введите отчество (при наличии): ")
  phones = []
  phone = input("Введите номер телефона (или Enter для окончания ввода): ")
  while phone:
      if validate_phone_number(phone):
          phones.append(phone)
          phone = input("Введите следующий номер телефона (или Enter для окончания ввода): ")
      else:
          print("Некорректный формат номера телефона. Попробуйте снова.")
          phone = input("Введите номер телефона (или Enter для окончания ввода): ")
  if not phones:
      print("Должен быть хотя бы один номер телефона. Контакт не сохранен.")
      return None, None, None, None, None, None
  email = input("Введите email (при наличии): ").strip() or None
  if email and not validate_email(email):
      print("Некорректный формат email. Контакт не сохранен.")
      return None, None, None, None, None, None
  dob = input("Введите дату рождения (при наличии): ").strip() or None
  if dob and not validate_date(dob):
      print("Некорректный формат даты рождения. Контакт не сохранен.")
      return None, None, None, None, None, None
  return last_name, first_name, middle_name, phones, email, dob

def get_search_query():
  """Получает от пользователя критерий поиска контактов."""
  return input("Введите критерий поиска (имя, фамилию, отчество, номер телефона, email или дату рождения): ")

def get_edit_details():
  """Получает от пользователя новые данные для редактирования контакта."""
  identifier = input("Введите имя, фамилию, отчество, номер телефона, email или дату рождения контакта для редактирования: ")
  new_last_name = input("Введите новую фамилию (или Enter, чтобы оставить без изменений): ")

  new_first_name = input("Введите новое имя (или Enter, чтобы оставить без изменений): ")
  new_middle_name = input("Введите новое отчество (или Enter, чтобы оставить без изменений): ")
  new_phones = []
  phone = input("Введите новый номер телефона (или Enter для окончания ввода): ")
  while phone:
     if validate_phone_number(phone):
         new_phones.append(phone)
         phone = input("Введите следующий новый номер телефона (или Enter для окончания ввода): ")
     else:
         print("Некорректный формат номера телефона. Попробуйте снова.")
         phone = input("Введите новый номер телефона (или Enter для окончания ввода): ")
  new_email = input("Введите новый email (или Enter, чтобы оставить без изменений): ").strip() or None
  if new_email and not validate_email(new_email):
     print("Некорректный формат email. Контакт не сохранен.")
     return None, None, None, None, None, None, None
  new_dob = input("Введите новую дату рождения (или Enter, чтобы оставить без изменений): ").strip() or None
  if new_dob and not validate_date(new_dob):
     print("Некорректный формат даты рождения. Контакт не сохранен.")
     return None, None, None, None, None, None, None
  return identifier, new_last_name, new_first_name, new_middle_name, new_phones, new_email, new_dob

def main():
   global contacts
   db_path = get_database_path()
   conn = create_database(db_path)
   if conn is None:
       return
   contacts = load_contacts(conn)

   while True:
       print("\nМеню:")
       print("1. Показать все контакты")
       print("2. Добавить контакт")
       print("3. Поиск контактов")
       print("4. Редактировать контакт")
       print("5. Удалить номер телефона")
       print("6. Удалить контакт")
       print("7. Выход")
       choice = input("Выберите действие (1-7): ")

       if choice == '1':
           display_contacts(contacts)
       elif choice == '2':
           last_name, first_name, middle_name, phones, email, dob = get_contact_details()
           if last_name is not None:
               save_contact(conn, last_name, first_name, middle_name, phones, email, dob)
               contacts = load_contacts(conn)
       elif choice == '3':
           query = get_search_query()
           results = search_contacts(conn, query)
           display_contacts(results)
       elif choice == '4':
           identifier, new_last_name, new_first_name, new_middle_name, new_phones, new_email, new_dob = get_edit_details()
           if identifier is not None:
               edit_contact(conn, identifier, new_last_name=new_last_name if new_last_name else None, new_first_name=new_first_name if new_first_name else None, new_middle_name=new_middle_name if new_middle_name else None, new_phones=new_phones if new_phones else None, new_email=new_email, new_dob=new_dob)
       elif choice == '5':
           contact_identifier = input("Введите имя, фамилию, отчество, номер телефона или email контакта для удаления номера телефона: ")
           delete_phone_number(conn, contact_identifier)
       elif choice == '6':
           contact_identifier = input("Введите имя, фамилию, отчество, номер телефона или email контакта для удаления: ")
           delete_contact(conn, contact_identifier)
       elif choice == '7':
           conn.close()
           break
       else:
           print("Неверный выбор. Попробуйте снова.")

if __name__ == '__main__':
   main()
