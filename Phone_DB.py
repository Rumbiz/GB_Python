import sqlite3
import re

def create_database(db_path):
    """Создает или подключается к базе данных SQLite и создает таблицы contacts и phone_numbers."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    conn.commit()
    return conn

def load_contacts(conn):
    """Загружает контакты и связанные с ними номера телефонов из базы данных SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT c.last_name, c.first_name, c.middle_name, c.email, c.dob, group_concat(pn.phone_number, ',') FROM contacts c LEFT JOIN phone_numbers pn ON c.id = pn.contact_id GROUP BY c.id")
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
    cursor.execute(update_query, update_values)
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
   cursor.execute("""
       SELECT c.last_name, c.first_name, c.middle_name, c.email, c.dob, group_concat(pn.phone_number, ',')
       FROM contacts c
       LEFT JOIN phone_numbers pn ON c.id = pn.contact_id
       WHERE c.last_name LIKE ? OR c.first_name LIKE ? OR c.middle_name LIKE ? OR c.email LIKE ? OR c.dob LIKE ? OR pn.phone_number LIKE ?
       GROUP BY c.id
   """, (f"%{query}%",) * 6)
   contacts = []
   for last_name, first_name, middle_name, email, dob, phone_numbers in cursor.fetchall():
       name = ' '.join((last_name, first_name, middle_name)).strip()
       phones = [phone.strip() for phone in phone_numbers.split(',')] if phone_numbers else []
       contacts.append({'name': name, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name, 'email': email, 'dob': dob, 'phones': phones})
   return contacts

def delete_phone_number(conn, contact_identifier, phone_number):
   """Удаляет номер телефона для указанного контакта."""
   cursor = conn.cursor()
   cursor.execute("""
       SELECT c.id
       FROM contacts c
       LEFT JOIN phone_numbers pn ON c.id = pn.contact_id
       WHERE (c.last_name LIKE ? OR c.first_name LIKE ? OR c.middle_name LIKE ? OR c.email LIKE ? OR pn.phone_number LIKE ?)
   """, (f"%{contact_identifier}%",) * 5)
   contact_ids = [row[0] for row in cursor.fetchall()]

   if not contact_ids:
       print("Контакт не найден.")
       return

   for contact_id in contact_ids:
       cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ? AND phone_number = ?", (contact_id, phone_number))
       if cursor.rowcount > 0:
           conn.commit()
           print(f"Номер телефона {phone_number} удален из контакта.")
       else:
           print(f"Номер телефона {phone_number} не найден для указанного контакта.")

def delete_contact(conn, contact_identifier):
   """Удаляет контакт по имени, фамилии, отчеству, номеру телефона или email."""
   cursor = conn.cursor()
   cursor.execute("""
       SELECT id
       FROM contacts
       WHERE last_name LIKE ? OR first_name LIKE ? OR middle_name LIKE ? OR email LIKE ?
   """, (f"%{contact_identifier}%",) * 4)
   contact_ids = [row[0] for row in cursor.fetchall()]

   if not contact_ids:
       print("Контакт не найден.")
       return

   for contact_id in contact_ids:
       cursor.execute("DELETE FROM phone_numbers WHERE contact_id = ?", (contact_id,))
       cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
   conn.commit()
   print("Контакт удален.")

def get_database_path():
   """Получает от пользователя путь к файлу базы данных."""
   return input("Введите имя файла базы данных, или Enter для значения по умолчанию").strip() or "contacts.db"

def get_contact_details():
   """Получает от пользователя детали нового контакта."""
   last_name = input("Введите фамилию: ")
   first_name = input("Введите имя: ")
   middle_name = input("Введите отчество (при наличии): ")
   phones = input("Введите номера телефонов через запятую: ").replace(' ', '').split(',')
   email = input("Введите email (при наличии): ").strip() or None
   dob = input("Введите дату рождения (при наличии): ").strip() or None
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
   new_phones = input("Введите новые номера телефонов через запятую (или Enter, чтобы оставить без изменений): ").replace(' ', '').split(',')
   new_email = input("Введите новый email (или Enter, чтобы оставить без изменений): ").strip() or None
   new_dob = input("Введите новую дату рождения (или Enter, чтобы оставить без изменений): ").strip() or None
   return identifier, new_last_name, new_first_name, new_middle_name, new_phones, new_email, new_dob

def get_delete_phone_details():
   """Получает от пользователя данные для удаления номера телефона."""
   contact_identifier = input("Введите имя, фамилию, отчество, номер телефона или email контакта для удаления номера телефона: ")
   phone_number = input("Введите номер телефона для удаления: ")
   return contact_identifier, phone_number

def get_delete_contact_details():
   """Получает от пользователя данные для удаления контакта."""
   contact_identifier = input("Введите имя, фамилию, отчество, номер телефона или email контакта для удаления: ")
   return contact_identifier
def main():
    global contacts
    db_path = get_database_path()
    conn = create_database(db_path)
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
            save_contact(conn, last_name, first_name, middle_name, phones, email, dob)
            contacts = load_contacts(conn)
        elif choice == '3':
            query = get_search_query()
            results = search_contacts(conn, query)
            display_contacts(results)
        elif choice == '4':
            identifier, new_last_name, new_first_name, new_middle_name, new_phones, new_email, new_dob = get_edit_details()
            edit_contact(conn, identifier, new_last_name=new_last_name if new_last_name else None, new_first_name=new_first_name if new_first_name else None, new_middle_name=new_middle_name if new_middle_name else None, new_phones=new_phones if new_phones else None, new_email=new_email, new_dob=new_dob)
        elif choice == '5':
            contact_identifier, phone_number = get_delete_phone_details()
            delete_phone_number(conn, contact_identifier, phone_number)
        elif choice == '6':
            contact_identifier = get_delete_contact_details()
            delete_contact(conn, contact_identifier)
        elif choice == '7':
            conn.close()
            break
        else:
            print("Неверный выбор. Попробуйте снова.")
main()
