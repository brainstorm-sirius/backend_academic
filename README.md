# Academic Collaboration Platform Backend

A modern REST API for a scientific social network that enables researchers to find collaborations, manage publications, and receive personalized recommendations based on scientific interests.

## Key Features

- **Authentication & Authorization**: JWT tokens, secure password hashing.
- **Profile Management**: Registration for researchers with support for IDs from scientific databases (ORCID, Google Scholar, Scopus, etc.).
- **Scientific Interests**: Flexible system for managing user research interests.
- **Publications**: Upload and manage publications via Excel/CSV files.
- **Search**: Unified search across registered users and unregistered authors.
- **Recommendations**: Personalized researcher recommendations based on interest matching.
- **Author Profiles**: Detailed profiles with publications, metrics, and analytics.
- **Knowledge Graph**: Visualization of connections between interests and researchers.
- **Data Import**: Bulk import of author data from CSV files.

## Tech Stack

### Backend
- **FastAPI** 0.115+: Modern asynchronous web framework.
- **Pydantic v2**: Data validation and serialization.
- **SQLAlchemy 2.x**: ORM for database interaction.
- **Uvicorn**: ASGI server.

### Database
- **SQLite** (default): Lightweight DB for development.
- PostgreSQL support via environment variables.

### Security
- **JWT** (`python-jose`): JSON Web Tokens for authentication.
- **bcrypt_sha256** (`passlib`): Secure password hashing.
- **CORS**: Configured for frontend interaction.

### Recommendations
- **scikit-learn**: KNN algorithm for finding similar researchers.
- **TF-IDF**: Text data vectorization.
- **pandas, numpy, scipy**: Data processing.

### Files
- **openpyxl**: Excel file processing.
- **pandas**: CSV file processing.

### Deployment
- **Docker** + **Docker Compose**: Containerization.
- **Health checks**: Application status monitoring.

## Requirements

- Python 3.11+
- Docker 20.10+ (optional, for containerization)
- SQLite 3 (built into Python) or PostgreSQL (for production)

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd backend_academic

# Create .env file (optional but recommended)
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env

# Start the application
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

The application will be available at: `http://localhost:8000`

### Option 2: Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd backend_academic

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export SECRET_KEY="your-secret-key"
export DATABASE_URL="sqlite:///./users.db"

# Start the application
uvicorn app.main:app --reload
```

The application will be available at: `http://127.0.0.1:8000`

## Documentation

- **API Documentation (Swagger)**: `http://localhost:8000/docs`
- **Alternative Documentation (ReDoc)**: `http://localhost:8000/redoc`
- **Health check**: `http://localhost:8000/health`


## System Architecture

The application is built using a multi-layer architecture:

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│         (app/main.py)                   │
├─────────────────────────────────────────┤
│  API Layer (Endpoints)                  │
│  - Authentication                       │
│  - User Management                      │
│  - Search & Recommendations             │
│  - Knowledge Graph                      │
├─────────────────────────────────────────┤
│  Business Logic Layer                   │
│  - Auth Service (app/auth.py)           │
│  - Recommender Service (app/recommender)│
├─────────────────────────────────────────┤
│  Data Access Layer                      │
│  - Models (app/models.py)               │
│  - Database (app/database.py)           │
├─────────────────────────────────────────┤
│  Data Validation Layer                  │
│  - Schemas (app/schemas.py)             │
└─────────────────────────────────────────┘
```

### System Components

1.  **API Layer** (`app/main.py`): Handles HTTP requests, validates input via Pydantic, and routes requests.
2.  **Authentication Service** (`app/auth.py`): Handles password hashing (bcrypt), JWT generation/validation, and dependency injection for current users.
3.  **Recommender Service** (`app/recommender.py`): Manages the KNN model loading, TF-IDF vectorization, and similarity searches.
4.  **Database Layer** (`app/database.py`, `app/models.py`): Manages DB connections, ORM models, and automatic table creation.
5.  **Validation Layer** (`app/schemas.py`): Pydantic schemas for input validation and response serialization.

## Database Structure

### Entity Relationship Diagram

```
┌─────────────┐
│    users    │
│─────────────│
│ id (PK)     │
│ login       │◄──────────┐
│ email       │           │
│ interests_  │           │
│   list      │           │
└─────────────┘           │
      │                   │
      │ 1:N               │
      │                   │
      ▼                   │
┌──────────────────┐      │
│ user_publications│      │
│──────────────────│      │
│ id (PK)          │      │
│ user_id (FK)     │──────┘
│ title            │
│ coauthors        │
│ citations        │
│ journal          │
│ publication_year │
└──────────────────┘

┌─────────────┐
│   authors   │
│─────────────│
│ id (PK)     │
│ author_id   │──┐
│ author_name │  │
│ title       │  │
│ journal     │  │
└─────────────┘  │
                 │ (logical link via author_id)
                 │
                 ▼
┌──────────────────┐
│ author_interests │
│──────────────────│
│ id (PK)          │
│ author_id (UK)   │◄──┘
│ author_name      │
│ interests_list   │
│ keywords_list    │
│ articles_count   │
│ interests_count  │
│ main_interest    │
└──────────────────┘
```

### Main Tables

#### `users` - Registered Users
- Stores data for registered researchers.
- Supports IDs from scientific databases (ORCID, Google Scholar, Scopus, WOS, RSCI).
- One-to-many relationship with `user_publications`.

#### `user_publications` - User Publications
- Stores publications of registered users.
- Uploaded via Excel/CSV files.
- Many-to-one relationship with `users`.

#### `authors` - Unregistered Authors
- Stores information about unregistered authors and their publications.
- Imported from CSV files.
- Logical link to `author_interests` via `author_id`.

#### `author_interests` - Author Scientific Interests
- Stores scientific interests of unregistered authors.
- Used for recommendations and search.
- Logical link to `authors` via `author_id`.

## Environment Variables

| Variable | Default Value | Purpose |
|-----------|-----------------------|-----------|
| `DATABASE_URL` | `sqlite:///./users.db` | Connection string (SQLAlchemy) |
| `SECRET_KEY` | `change-me` | JWT signing key (⚠️ **must change in production**) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token validity duration in minutes |

**Important**: In production, set a strong `SECRET_KEY`:
```bash
export SECRET_KEY=$(openssl rand -hex 32)
```

## API Endpoints

### Authentication

#### `POST /auth/register` - Register
Creates a new user in the system.

**Parameters**:
- `login` (string, min 3): Unique login.
- `email` (email): Email address.
- `first_name`, `last_name` (string): Name and surname.
- `password` (string, min 8): Password.
- `google_scholar_id`, `scopus_id`, `wos_id`, `rsci_id`, `orcid_id` (optional): Scientific database IDs.

#### `POST /auth/login` - Login
Returns a JWT token for authorized requests.

**Parameters**:
- `login_or_email` (string): Login or email.
- `password` (string): Password.

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Users

#### `GET /users/me` - Current User
Requires authorization. Returns current user data.

#### `PUT /users/interests` - Update Interests
Updates the user's list of scientific interests.

#### `POST /users/{user_id}/publications/upload` - Upload Publications
Uploads publications from an Excel or CSV file.

**Supported Formats**: CSV (.csv), Excel (.xlsx, .xls)

**Limits**:
- Max file size: 10MB
- Max rows: 10,000

#### `GET /users/{user_id}/publications` - Get Publications
Returns all publications for the specified user.

#### `DELETE /users/{user_id}/publications/{publication_id}` - Delete Publication
Deletes a user's publication.

### Search

#### `GET /search` - Unified Search
Searches across registered users (by username) and unregistered authors (by name).

**Parameters**:
- `query` (string, min 2): Search query.
- `limit` (int, 1-100, default 10): Max results.

#### `GET /search/users` - Search Users
Search strictly within registered users.

#### `GET /search/authors` - Search Authors
Search strictly within unregistered authors.

### Authors

#### `GET /authors/{author_id}/interests` - Author Interests
Returns scientific interests for an author via `author_id`.

#### `GET /authors/{author_id}/profile` - Full Author Profile
Returns a full author profile with publications and analytics.

**Response Includes**:
- Scientist info (name, ORCID, metrics).
- Analytics (h-index, average, productivity).
- Topic distribution.
- Publication list.

### Recommendations

#### `POST /recommend` - Get Recommendations
Uses the trained KNN model to find similar researchers.

**Parameters**:
- `interests` (array of strings): List of scientific interests.
- `publications` (array of strings, optional): List of publications for analysis.
- `num_recommendations` (int, 1-100, default 10): Number of recommendations.

**Ranking Algorithm**:
- Similarity (60%): Interest matching.
- Productivity (25%): Article count.
- Diversity (15%): Variety of interests.

### Knowledge Graph

#### `GET /knowledge-graph` - Graph Data
**Requires Authorization**: Yes (Bearer token)

Returns all unique interests and the top 100 most relevant scientists for the current user based on their scientific interests.

**Logic**:
1. Collects all unique interests from `users` and `author_interests`.
2. Counts scientists for each interest.
3. Selects top 100 relevant scientists (sorted by interest match).
4. Links scientists to interests via IDs.

### System

#### `GET /health` - Health Check
Returns application and model status.

**Response**:
```json
{
  "status": "healthy",
  "authors_count": 194850,
  "model_loaded": true
}
```

## Recommendation Model

The application uses a trained model for recommending scientists:

**Algorithm**: K-Nearest Neighbors (KNN) with cosine distance.
**Vectorization**: TF-IDF (Term Frequency-Inverse Document Frequency).
**Ranking Metrics**:
- Similarity (60%)
- Productivity (25%)
- Diversity (15%)

**Model Structure**:
- `authors_data.pkl`: Author data (DataFrame).
- `vectorizer.pkl`: TF-IDF vectorizer.
- `author_vectors.npz`: Vectorized author profiles.
- `knn_model.pkl`: Trained KNN model.

The model loads automatically from the `model/` directory at startup.

**Note**:
- The `model/` folder is **excluded from git** due to file size (~83MB).
- Obtain the pre-trained model from the team or train it yourself.

### Training the Model

To train a new model, use `train_model.py`:

```bash
# Ensure authors_scientific_interests.csv is in the project root
python train_model.py
```

## Data Import

To import data regarding unregistered authors:

```bash
python import_csv.py
```

The script imports:
- `authors_expanded_with_ids.csv` → `authors` table.
- `authors_scientific_interests.csv` → `author_interests` table.

**Note**:
- CSV files are **excluded from git** due to size (~127MB).
- Obtain CSV files from the team or generate them yourself.
- Ensure CSV files are in the project root before importing.

## Security

### Implemented Measures

- **SQL Injection**: Protected via SQLAlchemy ORM.
- **Passwords**: Hashed using bcrypt_sha256.
- **JWT Tokens**: Secure authentication.
- **Data Validation**: Pydantic schemas.
- **File Limits**: Max 10MB, 10,000 rows.
- **Error Handling**: Try-except blocks with rollback.

### Production Recommendations

- **SECRET_KEY**: Use a strong key.
- **HTTPS**: Mandatory for production.
- **CORS**: Restrict origins to specific domains.
- **Rate Limiting**: Consider adding rate limiting.
- **Monitoring**: Setup logging and monitoring.


## Project Structure

```
backend_academic/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── main.py             # FastAPI app and endpoints
│   ├── models.py           # SQLAlchemy models (DB tables)
│   ├── schemas.py          # Pydantic schemas (validation)
│   ├── auth.py             # Auth and JWT
│   ├── database.py         # DB connection setup
│   └── recommender.py      # Recommendation service (KNN)
├── model/                  # Trained model (not in git)
│   ├── authors_data.pkl
│   ├── vectorizer.pkl
│   ├── author_vectors.npz
│   └── knn_model.pkl
├── import_csv.py           # CSV import script
├── train_model.py          # Model training script
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore           # Docker exclusions
├── .gitignore              # Git exclusions
└── README.md               # Documentation
```

## Testing

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Request Examples

#### Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "login": "scientist123",
    "email": "scientist@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePass123",
    "orcid_id": "0000-0000-0000-0000"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login_or_email": "scientist123",
    "password": "SecurePass123"
  }'
```

#### Get Recommendations
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "interests": ["Machine Learning", "Deep Learning"],
    "num_recommendations": 10
  }'
```

## Docker



### Quick Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart
```

## Database Management

### SQLite (Default)

```bash
# Connect to DB
sqlite3 users.db

# View tables
.tables

# View users
SELECT * FROM users LIMIT 10;

# View publications
SELECT * FROM user_publications LIMIT 10;

# Exit
.quit
```

### Automatic Table Creation

All tables are automatically created on the first application run via `models.Base.metadata.create_all(bind=engine)` in `app/main.py`.

## Updates

```bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart application
docker-compose restart  # or uvicorn app.main:app --reload
```

## Troubleshooting

### Issue: Model fails to load

**Solution**: Ensure the `model/` folder contains all required files:
- `authors_data.pkl`
- `vectorizer.pkl`
- `author_vectors.npz`
- `knn_model.pkl`

### Issue: Error during CSV import

**Solution**:
- Verify CSV files are in the project root.
- Ensure files have correct encoding (UTF-8 with BOM).
- Check for required columns.

### Issue: Database is locked

**Solution**:
- Close all DB connections.
- Restart the application.
- For SQLite: Ensure no other processes are using the DB.
