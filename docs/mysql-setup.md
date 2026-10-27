# MySQL setup

ParkEase requires MySQL 8.0+ and uses InnoDB with `utf8mb4`.

1. Run `sql/00_create_database.sql` as a MySQL administrator.
2. Create a least-privilege MySQL application user with access only to `parkease`.
3. Set `DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/parkease` in a local `.env` file.
4. Run `sql/01_users.sql`, then `sql/02_parkease_schema.sql` while connected to `parkease`.
5. Run `flask --app app create-admin` to create the first administrator.

The generated unique keys in `parking_sessions` enforce one active session per vehicle and per slot. Use a database transaction and row locking when assigning/releasing a slot.
