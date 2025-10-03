#!/usr/bin/env python3
"""
RCIP Recipe Collection Agent

A comprehensive recipe collection and conversion system that automatically
searches, scrapes, and converts recipes to the RCIP (Recipe Collection 
Interchange Protocol) format.

Features:
- Web scraping from multiple recipe sources
- DuckDuckGo search integration (free)
- Groq LLM integration for recipe conversion
- Interactive and batch processing modes
- Automatic version control and duplicate handling
- RCIP format validation and conversion

Author: RCIP Agent System
Version: 1.0.0
License: MIT

Dependencies:
- groq: LLM API for recipe conversion
- ddgs: DuckDuckGo search integration
- beautifulsoup4: Web scraping
- requests: HTTP requests
- flask: Web viewer (optional)
- python-dotenv: Environment variable management

Usage:
    python rcip_agent.py

Environment Variables:
    GROQ_API_KEY: Required API key for Groq LLM service
"""

import os
import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Imports for search and parsing
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup

# Groq LLM
from groq import Groq

# Load environment variables
load_dotenv()


class RCIPAgent:
    """Agent for searching and converting recipes to RCIP format"""

    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Initialize Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env file!")

        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"  # Cheapest model!

        print(f"[OK] RCIP Agent initialized")
        print(f"   LLM: Groq ({self.model})")
        print(f"   Search: DuckDuckGo (free)")
        print(f"   Output: {self.output_dir.absolute()}")

    def search_recipe(self, query: str, max_results: int = 3) -> list:
        """
        Search for recipes using DuckDuckGo

        Args:
            query: Dish name
            max_results: Number of results

        Returns:
            list: List of recipe URLs
        """
        print(f"\n[SEARCH] Searching for recipe: '{query}'")

        try:
            # DuckDuckGo search (free!)
            search_query = f"{query} recipe with photos step by step"

            with DDGS() as ddgs:
                results = list(ddgs.text(
                    search_query,
                    max_results=max_results,
                    region='en-us'
                ))

            urls = []
            for i, result in enumerate(results, 1):
                url = result.get('href', result.get('link', ''))
                title = result.get('title', '')
                print(f"   {i}. {title}")
                print(f"      {url}")
                urls.append(url)

            return urls

        except Exception as e:
            print(f"[ERROR] Search error: {e}")
            return []

    def scrape_recipe(self, url: str) -> dict:
        """
        Parse recipe from web page

        Args:
            url: URL of the recipe page

        Returns:
            dict: Extracted recipe data
        """
        print(f"\n[PARSING] Parsing page...")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            # Extract text (simple method, can be improved)
            # Remove script and style tags
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text = soup.get_text(separator='\n', strip=True)

            # Limit size (to save tokens)
            lines = text.split('\n')
            filtered_lines = [line for line in lines if len(line) > 20]
            # First 100 meaningful lines
            text = '\n'.join(filtered_lines[:100])

            print(f"   [OK] Extracted {len(text)} characters")

            return {
                'url': url,
                'text': text
            }

        except Exception as e:
            print(f"   [ERROR] Parsing error: {e}")
            return None

    def convert_to_rcip(self, recipe_data: dict, recipe_name: str) -> dict:
        """
        Convert recipe text to RCIP format
        Uses hybrid approach: local parser + LLM for improvement

        Args:
            recipe_data: Data from website
            recipe_name: Recipe name

        Returns:
            dict: Recipe in RCIP format
        """
        print(f"\n[AI] Converting to RCIP...")

        try:
            # Import converter
            from rcip_converter import RCIPConverter

            converter = RCIPConverter()

            # Try to extract structured data
            ingredients_text, steps_text = self._extract_structured_text(
                recipe_data['text'])

            if ingredients_text and steps_text:
                print(f"   [OK] Using local parser")

                # Local conversion (fast and free!)
                rcip_recipe = converter.convert(
                    name=recipe_name,
                    ingredients_text=ingredients_text,
                    steps_text=steps_text,
                    source_url=recipe_data['url']
                )

            else:
                print(f"   [OK] Using LLM for unstructured text")

                # Use LLM for complex cases
                rcip_recipe = self._convert_with_llm(recipe_data, recipe_name)

            if rcip_recipe:
                print(f"   [OK] Conversion successful!")
                print(
                    f"   - Ingredients: {len(rcip_recipe.get('ingredients', []))}")
                print(f"   - Steps: {len(rcip_recipe.get('steps', []))}")

            return rcip_recipe

        except Exception as e:
            print(f"   [WARNING] Local parser failed, using LLM")
            return self._convert_with_llm(recipe_data, recipe_name)

    def _extract_structured_text(self, text: str) -> tuple:
        """
        Extract ingredients and steps sections from text

        Returns:
            (ingredients_text, steps_text)
        """
        lines = text.split('\n')

        ingredients = []
        steps = []
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Determine section
            if any(word in line_lower for word in ['ingredient', 'ingredients', 'состав', 'нужно:', 'понадобится']):
                current_section = 'ingredients'
                continue
            elif any(word in line_lower for word in ['instruction', 'instructions', 'method', 'step', 'steps', 'приготовление', 'инструкция', 'способ', 'шаг']):
                current_section = 'steps'
                continue

            # Add to current section
            if current_section == 'ingredients':
                if re.match(r'^\d+[\s\w]+', line) or re.match(r'^[-•*]', line):
                    ingredients.append(line)
            elif current_section == 'steps':
                if re.match(r'^\d+[\.)]', line) or re.match(r'^[-•*]', line) or len(line) > 30:
                    steps.append(line)

        ingredients_text = '\n'.join(ingredients) if ingredients else None
        steps_text = '\n'.join(steps) if steps else None

        return ingredients_text, steps_text

    def _convert_with_llm(self, recipe_data: dict, recipe_name: str) -> dict:
        """Conversion using Groq LLM (fallback method)"""

        prompt = f"""Extract from the recipe text ONLY the list of ingredients and cooking steps.

NAME: {recipe_name}

TEXT:
{recipe_data['text'][:2500]}

Answer in format:

INGREDIENTS:
- 300g flour
- 2 eggs
...

STEPS:
1. Mix flour with eggs
2. Add milk
..."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system",
                        "content": "You extract ingredients and steps from recipes."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=2000
            )

            response = chat_completion.choices[0].message.content

            # Parse LLM response
            parts = response.split('STEPS:')
            if len(parts) == 2:
                ing_part = parts[0].replace('INGREDIENTS:', '').strip()
                steps_part = parts[1].strip()

                from rcip_converter import RCIPConverter
                converter = RCIPConverter()

                return converter.convert(
                    name=recipe_name,
                    ingredients_text=ing_part,
                    steps_text=steps_part,
                    source_url=recipe_data['url']
                )

        except Exception as e:
            print(f"   [ERROR] LLM conversion failed: {e}")
            return None

    def validate_rcip(self, recipe: dict) -> bool:
        """
        Simple validation of RCIP recipe

        Args:
            recipe: Recipe in RCIP format

        Returns:
            bool: True if valid
        """
        required_fields = ['rcip_version', 'id',
                           'meta', 'ingredients', 'steps']

        for field in required_fields:
            if field not in recipe:
                print(f"   [WARNING] Missing required field: {field}")
                return False

        # Check allergens in ingredients
        for ing in recipe.get('ingredients', []):
            if 'allergens' not in ing:
                print(
                    f"   [WARNING] Ingredient '{ing.get('name')}' missing allergens field")
                return False

        return True

    def get_existing_recipe_ids(self) -> set:
        """
        Get all existing recipe IDs from saved files

        Returns:
            set: Set of existing recipe IDs
        """
        existing_ids = set()

        for file_path in self.output_dir.glob("*.rcip"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    recipe_data = json.load(f)
                    if 'id' in recipe_data:
                        existing_ids.add(recipe_data['id'])
            except Exception as e:
                print(f"   [WARNING] Could not read {file_path}: {e}")

        return existing_ids

    def generate_unique_filename(self, recipe_name: str, recipe_id: str) -> str:
        """
        Generate unique filename for recipe

        Args:
            recipe_name: Name of the recipe
            recipe_id: Unique ID of the recipe

        Returns:
            str: Unique filename
        """
        # Create safe name from recipe title
        safe_name = "".join(c if c.isalnum() or c in (
            ' ', '-', '_') else '_' for c in recipe_name)
        safe_name = safe_name.replace(' ', '_').lower()

        # Use recipe ID as part of filename for uniqueness
        filename = f"{safe_name}_{recipe_id}.rcip"

        # Check if file already exists and create version number
        counter = 1
        base_filename = filename
        while (self.output_dir / filename).exists():
            name_part = base_filename.replace('.rcip', '')
            filename = f"{name_part}_v{counter}.rcip"
            counter += 1

        return filename

    def save_recipe(self, recipe: dict, filename: str = None) -> Path:
        """
        Save recipe to file with version control

        Args:
            recipe: RCIP recipe
            filename: Filename (optional)

        Returns:
            Path: Path to saved file
        """
        if not filename:
            # Generate unique filename using recipe ID
            recipe_name = recipe['meta']['name']
            recipe_id = recipe.get('id', str(uuid.uuid4()))
            filename = self.generate_unique_filename(recipe_name, recipe_id)

        filepath = self.output_dir / filename

        # Check if file already exists
        if filepath.exists():
            print(
                f"   [INFO] File {filename} already exists, creating new version...")
            # Generate versioned filename
            base_name = filepath.stem
            counter = 1
            while filepath.exists():
                new_filename = f"{base_name}_v{counter}.rcip"
                filepath = self.output_dir / new_filename
                counter += 1
            print(f"   [INFO] Saving as: {filepath.name}")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)

        print(f"\n[SAVE] Saved: {filepath}")
        return filepath

    def process_recipe(self, recipe_name: str, auto_save: bool = True) -> dict:
        """
        Full cycle: search → parse → convert → save

        Args:
            recipe_name: Recipe name
            auto_save: Auto-save

        Returns:
            dict: RCIP recipe or None
        """
        print(f"\n{'='*60}")
        print(f"[RECIPE] Processing recipe: {recipe_name}")
        print(f"{'='*60}")

        # 1. Search
        urls = self.search_recipe(recipe_name)
        if not urls:
            print("[ERROR] No recipes found")
            return None

        # 2. Parsing (try first 3 URLs)
        recipe_data = None
        for url in urls[:3]:
            recipe_data = self.scrape_recipe(url)
            if recipe_data and len(recipe_data.get('text', '')) > 500:
                break

        if not recipe_data:
            print("[ERROR] Failed to extract recipe text")
            return None

        # 3. Convert to RCIP
        rcip_recipe = self.convert_to_rcip(recipe_data, recipe_name)
        if not rcip_recipe:
            print("[ERROR] Conversion failed")
            return None

        # 4. Validation
        if not self.validate_rcip(rcip_recipe):
            print("[WARNING] Recipe failed validation, but saving anyway")

        # 5. Save with version control
        if auto_save:
            self.save_recipe(rcip_recipe)

        print(f"\n[SUCCESS] Recipe '{recipe_name}' processed successfully!")
        return rcip_recipe

    def batch_process(self, recipe_names: list):
        """
        Batch processing of recipe list

        Args:
            recipe_names: List of recipe names
        """
        print(f"\n{'='*60}")
        print(f"[BATCH] Batch processing: {len(recipe_names)} recipes")
        print(f"{'='*60}")

        results = {
            'success': [],
            'failed': []
        }

        for i, name in enumerate(recipe_names, 1):
            print(f"\n[{i}/{len(recipe_names)}]")

            try:
                recipe = self.process_recipe(name)
                if recipe:
                    results['success'].append(name)
                else:
                    results['failed'].append(name)
            except Exception as e:
                print(f"[ERROR] Critical error: {e}")
                results['failed'].append(name)

        # Results
        print(f"\n{'='*60}")
        print(f"[RESULTS] RESULTS")
        print(f"{'='*60}")
        print(f"[OK] Successful: {len(results['success'])}")
        print(f"[ERROR] Failed: {len(results['failed'])}")

        if results['failed']:
            print(f"\nFailed to process:")
            for name in results['failed']:
                print(f"  - {name}")

        return results

    def load_recipe_list(self, filename: str = "recipe_list.txt") -> list:
        """
        Load recipe list from file

        Args:
            filename: Path to recipe list file

        Returns:
            list: List of recipe names
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                recipes = [line.strip() for line in f if line.strip()]
            print(f"[INFO] Loaded {len(recipes)} recipes from {filename}")
            return recipes
        except FileNotFoundError:
            print(f"[ERROR] Recipe list file '{filename}' not found!")
            return []
        except Exception as e:
            print(f"[ERROR] Error loading recipe list: {e}")
            return []

    def list_existing_recipes(self):
        """
        List all existing recipes in output directory
        """
        print(f"\n[EXISTING RECIPES] Found recipes in {self.output_dir}:")
        print(f"{'='*60}")

        recipe_files = list(self.output_dir.glob("*.rcip"))

        if not recipe_files:
            print("No recipes found.")
            return

        for i, file_path in enumerate(recipe_files, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    recipe_data = json.load(f)
                    recipe_name = recipe_data.get(
                        'meta', {}).get('name', 'Unknown')
                    recipe_id = recipe_data.get('id', 'No ID')
                    print(
                        f"{i:2d}. {recipe_name} (ID: {recipe_id}) - {file_path.name}")
            except Exception as e:
                print(f"{i:2d}. Error reading {file_path.name}: {e}")

        print(f"{'='*60}")
        print(f"Total: {len(recipe_files)} recipes")


def show_menu():
    """Display the main menu"""
    print(f"\n{'='*60}")
    print(f"[MENU] RCIP Recipe Agent - Choose Mode")
    print(f"{'='*60}")
    print(f"1. Interactive mode - enter recipes one by one")
    print(f"2. Batch mode - process recipe list from file")
    print(f"3. View current recipe list")
    print(f"4. List existing recipes")
    print(f"5. Exit")
    print(f"{'='*60}")


def interactive_mode(agent):
    """Interactive recipe processing"""
    print(f"\n[INTERACTIVE] Enter recipe name to search and convert to RCIP format.")
    print(f"To return to menu, type 'menu' or 'back'")

    while True:
        try:
            # Ask user for recipe name
            recipe_name = input(f"\n[INPUT] Enter recipe name: ").strip()

            # Check return to menu commands
            if recipe_name.lower() in ['menu', 'back', 'm']:
                return

            # Check if user entered something
            if not recipe_name:
                print(f"[WARNING] Please enter a recipe name.")
                continue

            # Process recipe
            print(f"\n[PROCESSING] Processing recipe: '{recipe_name}'")
            result = agent.process_recipe(recipe_name)

            if result:
                print(
                    f"[SUCCESS] Recipe '{recipe_name}' processed and saved successfully!")
            else:
                print(f"[ERROR] Failed to process recipe '{recipe_name}'")

        except KeyboardInterrupt:
            print(f"\n\n[INFO] Returning to menu...")
            return
        except EOFError:
            print(f"\n[INFO] Returning to menu...")
            return
        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")
            print(f"[INFO] Try again or type 'menu' to return.")


def batch_mode(agent):
    """Batch recipe processing"""
    recipes = agent.load_recipe_list()

    if not recipes:
        print(f"[ERROR] No recipes loaded. Please check recipe_list.txt file.")
        return

    print(f"\n[INFO] Found {len(recipes)} recipes to process:")
    for i, recipe in enumerate(recipes, 1):
        print(f"  {i}. {recipe}")

    confirm = input(
        f"\n[CONFIRM] Process all {len(recipes)} recipes? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print(f"[INFO] Batch processing cancelled.")
        return

    # Process all recipes
    agent.batch_process(recipes)

    print(f"\n[INFO] Batch processing completed! Returning to menu...")


def view_recipe_list(agent):
    """View current recipe list"""
    recipes = agent.load_recipe_list()

    if not recipes:
        print(f"[ERROR] No recipes found in recipe_list.txt")
        return

    print(f"\n[RECIPE LIST] Current recipes ({len(recipes)} total):")
    print(f"{'='*40}")
    for i, recipe in enumerate(recipes, 1):
        print(f"{i:2d}. {recipe}")
    print(f"{'='*40}")


def main():
    """Main menu system"""

    # Create agent
    agent = RCIPAgent(output_dir="output")

    while True:
        try:
            show_menu()
            choice = input("Choose option (1-5): ").strip()

            if choice == "1":
                interactive_mode(agent)
            elif choice == "2":
                batch_mode(agent)
            elif choice == "3":
                view_recipe_list(agent)
            elif choice == "4":
                agent.list_existing_recipes()
            elif choice == "5":
                print(f"\n[INFO] Goodbye! Thank you for using RCIP Agent.")
                break
            else:
                print(f"[WARNING] Invalid choice. Please select 1-5.")

        except KeyboardInterrupt:
            print(f"\n\n[INFO] Program interrupted by user. Goodbye!")
            break
        except EOFError:
            print(f"\n[INFO] Input finished. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")
            print(f"[INFO] Try again or press Ctrl+C to exit.")


if __name__ == "__main__":
    main()
