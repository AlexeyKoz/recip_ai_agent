# RCIP Recipe Collection Agent

A comprehensive recipe collection and conversion system that automatically searches, scrapes, and converts recipes to the RCIP (Recipe Collection Interchange Protocol) format.

## 🚀 Features

### Core Functionality
- **Web Scraping**: Automatically extracts recipes from various websites
- **Search Integration**: Uses DuckDuckGo for free recipe discovery
- **AI Conversion**: Leverages Groq LLM for intelligent recipe parsing
- **RCIP Format**: Converts recipes to standardized RCIP v0.1 format
- **Version Control**: Automatic duplicate detection and versioning
- **Batch Processing**: Process multiple recipes from a list
- **Interactive Mode**: Real-time recipe processing

### Advanced Features
- **Allergen Detection**: Automatic identification of allergens in ingredients
- **Diet Classification**: Identifies vegetarian, vegan, and other dietary types
- **Multi-language Support**: English and Russian language support
- **Web Viewer**: Built-in Flask web interface for recipe browsing
- **File Management**: Organized output with unique filenames
- **Error Handling**: Robust error handling and recovery

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- Internet connection for web scraping and AI processing
- Groq API key (free tier available)

### Dependencies
```
groq>=0.4.0              # LLM API for recipe conversion
ddgs>=0.1.0              # DuckDuckGo search integration
beautifulsoup4>=4.12.0   # Web scraping
requests>=2.31.0         # HTTP requests
lxml>=4.9.0              # XML/HTML parsing
flask>=2.3.0             # Web viewer
werkzeug>=2.3.0          # WSGI utilities
python-dotenv>=1.0.0     # Environment variables
```

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd rcip-agent
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
```

Get your free Groq API key at: https://console.groq.com/

## 🎯 Usage

### Quick Start
```bash
python rcip_agent.py
```

### Menu Options
1. **Interactive Mode** - Enter recipes one by one
2. **Batch Mode** - Process recipe list from file
3. **View Recipe List** - See current recipes in list
4. **List Existing Recipes** - View all saved recipes
5. **Exit** - Quit the program

### Interactive Mode
```bash
# Start interactive mode
python rcip_agent.py
# Choose option 1
# Enter recipe name when prompted
# Example: "Chocolate Cake"
```

### Batch Processing
1. Edit `recipe_list.txt` with your desired recipes (one per line)
2. Run: `python rcip_agent.py`
3. Choose option 2 (Batch mode)
4. Confirm processing

### Web Viewer
```bash
# Start the web viewer
cd rcip_viewer
python recip_viewer.py
# Open: http://localhost:5000
```

## 📁 Project Structure

```
rcip-agent/
├── rcip_agent.py          # Main agent with menu system
├── rcip_converter.py       # Recipe conversion engine
├── rcip_viewer/           # Web viewer module
│   └── recip_viewer.py    # Flask web application
├── output/                # Generated recipe files (.rcip)
├── recipe_list.txt        # Batch processing recipe list
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔧 Configuration

### Recipe List File
Edit `recipe_list.txt` to customize batch processing:
```
Ukrainian Borscht
Chicken Noodle Soup
Caesar Salad
Apple Pie
American Pancakes
```

### Output Directory
Recipes are saved in the `output/` directory with automatic versioning:
- `apple_pie.rcip` (first version)
- `apple_pie_v1.rcip` (second version)
- `apple_pie_v2.rcip` (third version)

### Environment Variables
```env
# Required
GROQ_API_KEY=your_api_key_here

# Optional (for web viewer)
FLASK_ENV=development
FLASK_DEBUG=True
```

## 📊 RCIP Format

The system converts recipes to the standardized RCIP format:

```json
{
  "rcip_version": "0.1",
  "id": "rcip-unique-id",
  "meta": {
    "name": "Recipe Name",
    "description": "Recipe description",
    "author": "Source website",
    "created_at": "2024-01-01T00:00:00Z",
    "source_url": "https://example.com/recipe"
  },
  "ingredients": [
    {
      "name": "Flour",
      "amount": "300g",
      "allergens": ["gluten", "wheat"],
      "diet": ["vegetarian"]
    }
  ],
  "steps": [
    {
      "number": 1,
      "instruction": "Mix ingredients",
      "time": "5 minutes"
    }
  ]
}
```

## 🚨 Error Handling

### Common Issues

**1. API Key Error**
```
ValueError: GROQ_API_KEY not found in .env file!
```
**Solution**: Add your Groq API key to `.env` file

**2. Network Timeout**
```
requests.exceptions.Timeout
```
**Solution**: Check internet connection, try again

**3. No Recipes Found**
```
[ERROR] No recipes found
```
**Solution**: Try different recipe name or check search terms

**4. Conversion Failed**
```
[ERROR] Conversion failed
```
**Solution**: Recipe text may be too short or unstructured

### Debug Mode
Enable detailed logging by setting environment variable:
```bash
export DEBUG=True
python rcip_agent.py
```

## 🔄 Version Control

The system automatically handles recipe versions:
- **Unique IDs**: Each recipe gets a unique identifier
- **No Overwriting**: Existing recipes are never lost
- **Version Numbers**: Duplicates get `_v1`, `_v2` suffixes
- **File Safety**: All versions are preserved

## 🌐 Web Viewer Features

### Recipe Gallery
- Thumbnail view of all recipes
- Search and filter capabilities
- Recipe metadata display
- Quick access to recipe details

### Recipe Details
- Full ingredient list with allergens
- Step-by-step instructions
- Nutritional information
- Source attribution
- Cooking time and difficulty

### File Management
- Upload new recipes
- Delete unwanted recipes
- Export recipe data
- Batch operations

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest

# Format code
black *.py

# Lint code
flake8 *.py
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to all functions
- Write tests for new features

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

### Getting Help
1. Check the error messages and solutions above
2. Verify your API key is correct
3. Ensure all dependencies are installed
4. Check your internet connection

### Reporting Issues
When reporting issues, please include:
- Python version
- Operating system
- Error messages
- Steps to reproduce
- Recipe names that failed

## 🔮 Future Enhancements

- [ ] Additional recipe sources
- [ ] Nutritional analysis integration
- [ ] Recipe recommendation system
- [ ] Mobile app interface
- [ ] Cloud storage integration
- [ ] Recipe sharing features
- [ ] Advanced search filters
- [ ] Recipe scaling calculator

## 📈 Performance

### Processing Times
- **Simple recipes**: 10-30 seconds
- **Complex recipes**: 30-60 seconds
- **Batch processing**: ~1 minute per recipe
- **Web viewer**: Instant loading

### Resource Usage
- **Memory**: ~50MB base usage
- **CPU**: Low during idle, moderate during processing
- **Network**: ~1-5MB per recipe
- **Storage**: ~10-50KB per recipe file

---

**Happy Cooking! 🍳👨‍🍳👩‍🍳**
