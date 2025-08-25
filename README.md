# Fashion Store E-commerce Website

A complete e-commerce solution built with Flask, MongoDB, and modern web technologies.

## Features

### Customer Features
- **Product Browsing**: Browse products with filters (category, price, size, color)
- **Search**: Full-text search across product names and descriptions
- **Shopping Cart**: Add/remove items, quantity management
- **Checkout**: Shipping information and payment (COD/dummy card)
- **Order History**: View past orders and current status
- **User Profile**: Manage account information

### Admin Features
- **Product Management**: Add, edit, delete products with multiple images
- **Inventory Control**: Stock management per size with real-time updates
- **Order Management**: View, update status, and manage all orders
- **Category Management**: Organize products by categories
- **User Management**: View and manage customer accounts
- **Dashboard**: Analytics and overview of store performance

### Technical Features
- **Responsive Design**: Mobile-first approach with Bootstrap 5.3.0
- **Image Management**: Automatic optimization and GridFS storage
- **Security**: Role-based access control, CSRF protection, input validation
- **Email Notifications**: Automated order confirmations and status updates
- **Localization**: Indian Rupee formatting and IST timezone support

## Tech Stack

- **Backend**: Python Flask
- **Database**: MongoDB with GridFS for image storage
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.3.0
- **Authentication**: Flask-Login with bcrypt password hashing
- **Image Processing**: Pillow (PIL) for optimization
- **Email**: SMTP with HTML templates
- **Icons**: Font Awesome 6.0.0

## Installation

### Prerequisites
- Python 3.8+
- MongoDB (local or Atlas)
- pip package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ecommerce
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-super-secret-key-change-this-in-production
   MONGODB_URI=mongodb://localhost:27017/ecommerce
   UPLOAD_FOLDER=static/images/products
   MAX_CONTENT_LENGTH=16777216
   ALLOWED_EXTENSIONS=png,jpg,jpeg,gif,webp
   
   # Email Configuration (Optional)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_USE_TLS=true
   SMTP_FROM=Fashion Store <your-email@gmail.com>
   ```

5. **Database Setup**
   - Start MongoDB service
   - The application will automatically create the database and collections on first run
   - An admin user will be created with:
     - Email: `admin@fashionstore.com`
     - Password: `admin123`

6. **Run the application**
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`

## Admin User Creation

The application provides multiple ways to create admin users:

### 1. Automatic Creation (Default)
When you first run the application, it automatically creates a default admin user:
- **Email**: `admin@fashionstore.com`
- **Password**: `admin123`
- **Role**: `admin`

### 2. Web Interface
Visit `/create-admin` in your browser to create admin users through a web form:
- Navigate to `http://localhost:5000/create-admin`
- Fill in email and password
- Submit to create the admin user

### 3. Command Line Script
Use the standalone script for programmatic admin user creation:

```bash
# Interactive mode
python create_admin.py

# Direct mode
python create_admin.py admin@example.com mypassword
```

**Note**: The web interface and command-line script are development tools. In production, remove the `/create-admin` route or protect it with additional security measures.

## Email Configuration

### SMTP Setup
The application supports automated email notifications for:
- Order confirmations
- Order status updates

#### Gmail Setup
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use the generated password in `SMTP_PASSWORD`

#### Other Providers
- **Outlook/Hotmail**: Use `smtp-mail.outlook.com:587`
- **Yahoo**: Use `smtp.mail.yahoo.com:587`
- **Custom SMTP**: Use your provider's SMTP settings

#### Environment Variables
```env
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
SMTP_FROM=Store Name <your-email@domain.com>
```

### Email Templates
Professional HTML email templates are located in `templates/emails/`:
- `order_confirmation.html` - Sent when orders are placed
- `order_status_update.html` - Sent when order status changes

## Project Structure

```
ecommerce/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── static/
│   ├── css/
│   │   └── style.css    # Custom styles
│   ├── js/
│   │   └── main.js      # Client-side JavaScript
│   └── images/
│       └── products/    # Optimized product images
├── templates/
│   ├── base.html        # Base template
│   ├── home.html        # Homepage
│   ├── products.html    # Product listing
│   ├── product_detail.html
│   ├── cart.html        # Shopping cart
│   ├── checkout.html    # Checkout process
│   ├── profile.html     # User profile
│   ├── order_confirmation.html
│   ├── login.html       # Authentication
│   ├── register.html
│   ├── admin/           # Admin templates
│   │   ├── dashboard.html
│   │   ├── products.html
│   │   ├── product_form.html
│   │   ├── orders.html
│   │   ├── order_detail.html
│   │   ├── categories.html
│   │   └── users.html
│   └── emails/          # Email templates
│       ├── order_confirmation.html
│       └── order_status_update.html
└── README.md
```

## Database Schema

### Collections

#### Users
```json
{
  "_id": "ObjectId",
  "email": "user@example.com",
  "password_hash": "hashed_password",
  "role": "customer|admin",
  "created_at": "datetime"
}
```

#### Products
```json
{
  "_id": "ObjectId",
  "name": "Product Name",
  "description": "Product description",
  "price": 99.99,
  "category": "ObjectId",
  "colors": ["Red", "Blue"],
  "stock": {
    "S": 10,
    "M": 15,
    "L": 8
  },
  "images": ["image1.jpg", "image2.jpg"],
  "featured": true,
  "created_at": "datetime"
}
```

#### Orders
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "items": [
    {
      "product_id": "ObjectId",
      "size": "M",
      "quantity": 2,
      "price": 99.99
    }
  ],
  "shipping_address": {
    "name": "Customer Name",
    "address": "123 Street",
    "city": "City",
    "postal_code": "12345",
    "phone": "+1234567890"
  },
  "total_amount": 199.98,
  "status": "pending|processing|shipped|delivered|cancelled",
  "created_at": "datetime"
}
```

#### Categories
```json
{
  "_id": "ObjectId",
  "name": "Category Name",
  "description": "Category description"
}
```

## API Endpoints

### Public Routes
- `GET /` - Homepage
- `GET /products` - Product listing with filters
- `GET /product/<id>` - Product details
- `GET /cart` - Shopping cart
- `POST /cart/add` - Add item to cart
- `POST /cart/remove` - Remove item from cart
- `GET /checkout` - Checkout page
- `POST /checkout` - Process order
- `GET /profile` - User profile (login required)
- `GET /register` - User registration
- `POST /register` - Create user account
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - Logout user

### Admin Routes
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/products` - Product management
- `GET /admin/product/new` - Add new product
- `POST /admin/product/new` - Create product
- `GET /admin/product/edit/<id>` - Edit product
- `POST /admin/product/edit/<id>` - Update product
- `POST /admin/product/delete/<id>` - Delete product
- `POST /admin/product/update_stock/<id>` - Update stock
- `GET /admin/orders` - Order management
- `GET /admin/order/<id>` - Order details
- `POST /admin/order/update_status/<id>` - Update order status
- `GET /admin/categories` - Category management
- `POST /admin/category/new` - Create category
- `POST /admin/category/delete/<id>` - Delete category
- `GET /admin/users` - User management

## Security Features

- **Password Hashing**: bcrypt for secure password storage
- **Session Management**: Flask-Login for user sessions
- **CSRF Protection**: Built-in Flask-WTF protection
- **Input Validation**: Server-side validation for all forms
- **File Upload Security**: File type and size restrictions
- **Role-Based Access**: Admin-only routes protected
- **SQL Injection Protection**: MongoDB driver protection

## Image Management

### Storage Strategy
- **Original Images**: Stored in MongoDB GridFS for backup
- **Optimized Images**: Saved locally in `/static/images/products/`
- **Automatic Optimization**: Pillow processes uploads for web use
- **Multiple Images**: Support for multiple product images

### Image Processing
- Automatic resizing and optimization
- Web-friendly formats (JPEG, PNG, WebP)
- Metadata preservation
- File size reduction

## Customization

### Styling
- Modify `static/css/style.css` for custom styles
- Update Bootstrap theme variables
- Customize color scheme and typography

### Templates
- Edit Jinja2 templates in `templates/` directory
- Modify email templates in `templates/emails/`
- Update base template for site-wide changes

### Configuration
- Environment variables for easy configuration
- Database connection settings
- Email SMTP configuration
- File upload limits

## Deployment

### Production Considerations
- Use Gunicorn or uWSGI instead of Flask development server
- Set `FLASK_ENV=production`
- Configure MongoDB with authentication
- Use environment variables for sensitive data
- Enable HTTPS with SSL certificates
- Set up reverse proxy (Nginx/Apache)

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### Environment Variables for Production
```env
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
MONGODB_URI=mongodb://user:pass@host:port/database
SMTP_HOST=smtp.provider.com
SMTP_USER=production-email@domain.com
SMTP_PASSWORD=production-password
```

## Troubleshooting

### Common Issues

#### MongoDB Connection
- Ensure MongoDB service is running
- Check connection string in `.env`
- Verify network access for remote MongoDB

#### Email Not Sending
- Check SMTP configuration in `.env`
- Verify email credentials
- Check firewall/network restrictions
- Test with different SMTP providers

#### Image Upload Issues
- Verify upload folder permissions
- Check file size limits
- Ensure supported file types
- Check available disk space

#### Performance Issues
- Enable MongoDB indexes
- Optimize image sizes
- Use CDN for static assets
- Implement caching strategies

### Debug Mode
For development, enable debug mode:
```python
app.run(debug=True, use_reloader=False)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Email: info@fashionstore.com
- Create an issue in the repository
- Check the troubleshooting section

---

**Note**: This is a demonstration project. For production use, ensure proper security measures, error handling, and testing are implemented.
