# API Integration Challenge

Automated solver for mathematical problems expressed in natural language using AI and multiple external APIs.

## Features

- Natural language interpretation using GPT-4o-mini
- Integration with multiple REST APIs
- Automatic expression evaluation
- Caching system for optimization
- Connection pooling for performance
- https://recruiting.adere.so/challenge/instructions

## Setup

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:

```bash
git clone https://github.com/mtsantiago1230/api-integration-challenge.git
cd api-integration-challenge
```

2. Create virtual environment:

```bash
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create `.env` file with your credentials:

```env
API_TOKEN=your_token_here
```

## Usage

Run the solver:

```bash
python index.py
```

Options:

1. Practice mode - Test with sample problems
2. Real challenge - 3-minute timed challenge
3. Quick practice - Run 5 practice rounds

## Architecture

- **AI Integration**: Uses LLM for natural language understanding
- **API Orchestration**: Coordinates multiple external APIs
- **Caching**: LRU cache for repeated queries
- **Error Handling**: Retry logic with exponential backoff

## Technologies

- Python 3.x
- Requests (HTTP client)
- python-dotenv (Environment variables)
- OpenAI GPT-4o-mini (via proxy)

## License

MIT
