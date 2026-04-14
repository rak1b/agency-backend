# Payment Terminal Inventory Management System

[![License: MIT](https://img.shields.io/badge/license-MIT-orange)](./LICENSE)
[![Demo](https://img.shields.io/badge/demo-online-blue.svg)](https://inv.payinpos.com/)
[![API Docs](https://img.shields.io/badge/api-docs-blue.svg)](https://inventory.payinpos.com/api/docs/)

A Django-based application to manage inventory, status, Order, and deployment of payment terminals across multiple locations.

## Features

- **Authentication**: Token-based authentication (DRF Token / JWT).
- **Terminal CRUD**: Create, Read, Update, and Delete payment terminal records.
- **Order CRUD**: Create, Read, Update, and Delete terminal order records.
- **Live Tracking**: Live tracking for Devices.
- **Real-time Status**: Monitor terminal status (online/offline, in-use/available).
- **Location Management**: Assign terminals to business locations or administrators.
- **User Roles & Permissions**: Admin, Manager, and Technician roles with granular access control.
- **RESTful API**: Full API to integrate with external systems or mobile apps.

## Live Demo

Explore the application live:

> 🌐 [View Demo](https://payment-terminal-inventory-demo.herokuapp.com)

## API Documentation

Full API reference, including request/response schemas and examples:

> 📖 [Read the API Docs](https://inventory.payinpos.com/api/docs/)

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL (or MySQL for local development)
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Pax-Paymentsave/Inventory-Backend.git
   cd terminal-inventory-django
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```ini
   DEBUG=True
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgres://user:password@localhost:5432/terminal_db
   ```

5. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

Access the app at `http://127.0.0.1:8000/`.

## Usage

- **Admin Panel**: Manage users, roles, and terminals via Django admin at `/admin/`.
- **User Interface**: Login and navigate to the dashboard to view and manage terminals.
- **API**: Access endpoints under `/api/v1/`. Use the provided token to authenticate requests.

## API Endpoints

| Method | Endpoint                   | Description                         |
|--------|----------------------------|-------------------------------------|
| GET    | `/api/v1/inventory/web/product/`       | List all terminals                  |
| POST   | `/api/v1/inventory/web/product/`       | Create a new terminal               |
| GET    | `/api/v1/inventory/web/product/{slug}/`  | Retrieve terminal details           |
| PUT    | `/api/v1/inventory/web/product/{slug}/`  | Update terminal information         |
| DELETE | `/api/v1/inventory/web/product/{slug}/`  | Delete a terminal                   |
| POST   | `/api/v1/auth/web/token/`      | Obtain authentication token         |

_For full list and detailed examples, see the [API Documentation](https://inventory.payinpos.com/api/docs/)._ 

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

---
Built with ❤️ by Devsstream@2025 using Django & Django REST Framework.