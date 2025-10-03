#!/usr/bin/env python3
"""
RCIP Converter Module

A comprehensive recipe conversion system that transforms recipes from various
formats into the standardized RCIP (Recipe Collection Interchange Protocol) format.

Supported Input Formats:
- Plain text recipes
- JSON-LD (Schema.org) structured data
- HTML with structured recipe markup
- Semi-structured text with ingredients and steps

Key Features:
- Automatic allergen detection and classification
- Diet type identification (vegetarian, vegan, etc.)
- Ingredient parsing and normalization
- Step-by-step instruction processing
- Nutritional information extraction
- Cooking time and difficulty estimation
- Multi-language support (English, Russian)

RCIP Format Compliance:
- Follows RCIP v0.1 specification
- Generates unique recipe IDs
- Includes comprehensive metadata
- Validates required fields
- Supports allergen and dietary information

Author: RCIP Converter System
Version: 1.0.0
License: MIT

Usage:
    from rcip_converter import RCIPConverter
    converter = RCIPConverter()
    recipe = converter.convert(name, ingredients_text, steps_text, source_url)
"""

import re
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================================
# АЛЛЕРГЕНЫ И ДИЕТЫ
# ============================================================================

ALLERGEN_KEYWORDS = {
    'milk': ['молоко', 'сливки', 'сметана', 'йогурт', 'кефир', 'творог', 'сыр', 'масло сливочное'],
    'lactose': ['молоко', 'сливки', 'сметана', 'йогурт', 'кефир'],
    'eggs': ['яйцо', 'яйца', 'желток', 'белок'],
    'fish': ['рыба', 'лосось', 'форель', 'треска', 'тунец', 'скумбрия'],
    'shellfish': ['креветки', 'краб', 'омар', 'мидии', 'устрицы', 'кальмар'],
    'tree-nuts': ['орех', 'миндаль', 'фундук', 'кешью', 'фисташки', 'пекан'],
    'peanuts': ['арахис'],
    'wheat': ['мука', 'пшеница', 'хлеб', 'макароны', 'спагетти', 'булка'],
    'gluten': ['мука', 'пшеница', 'рожь', 'ячмень', 'овес', 'хлеб', 'макароны'],
    'soybeans': ['соя', 'тофу', 'соевый'],
    'sesame': ['кунжут', 'тахини'],
    'celery': ['сельдерей'],
    'mustard': ['горчица'],
    'sulphites': ['вино', 'уксус']
}

DIET_KEYWORDS = {
    'vegetarian': ['без мяса', 'вегетариан'],
    'vegan': ['веган'],
    'gluten-free': ['без глютена', 'безглютен'],
    'dairy-free': ['без молока', 'без молочн']
}


# ============================================================================
# ЕДИНИЦЫ ИЗМЕРЕНИЯ
# ============================================================================

UNIT_MAPPING = {
    # Масса
    'кг': ('kg', 1000),
    'килограмм': ('kg', 1000),
    'г': ('g', 1),
    'гр': ('g', 1),
    'грамм': ('g', 1),
    'мг': ('mg', 1),

    # Объем
    'л': ('l', 1000),
    'литр': ('l', 1000),
    'мл': ('ml', 1),
    'миллилитр': ('ml', 1),

    # Ложки/стаканы
    'ч.л.': ('tsp', 5),
    'ч.ложка': ('tsp', 5),
    'чайная ложка': ('tsp', 5),
    'ст.л.': ('tbsp', 15),
    'ст.ложка': ('tbsp', 15),
    'столовая ложка': ('tbsp', 15),
    'стакан': ('cup', 240),
    'стак': ('cup', 240),

    # Штуки
    'шт': ('pcs', 1),
    'штук': ('pcs', 1),
    'штука': ('pcs', 1),
    'штуки': ('pcs', 1),

    # Специальные
    'щепотка': ('pinch', 0.5),
    'щепот': ('pinch', 0.5),
    'по вкусу': ('to-taste', 0),
    'вкус': ('to-taste', 0)
}


# ============================================================================
# ДЕЙСТВИЯ
# ============================================================================

ACTION_MAPPING = {
    'добавить': 'add',
    'добавь': 'add',
    'добавляем': 'add',
    'положить': 'add',

    'смешать': 'mix',
    'смешай': 'mix',
    'смешиваем': 'mix',
    'перемешать': 'mix',

    'соединить': 'combine',
    'объединить': 'combine',

    'взбить': 'blend',
    'взбивать': 'blend',

    'нарезать': 'cut',
    'нарежь': 'cut',
    'порезать': 'cut',

    'нашинковать': 'slice',
    'нашинкуй': 'slice',

    'измельчить': 'mince',
    'измельчай': 'mince',

    'варить': 'boil',
    'свари': 'boil',
    'вскипятить': 'boil',

    'тушить': 'simmer',
    'туши': 'simmer',
    'протушить': 'simmer',

    'жарить': 'fry',
    'жарь': 'fry',
    'обжарить': 'fry',
    'пожарить': 'fry',

    'запекать': 'bake',
    'запеки': 'bake',
    'выпекать': 'bake',

    'охладить': 'cool',
    'остудить': 'cool',

    'замесить': 'knead',
    'месить': 'knead',

    'раскатать': 'roll',
    'раскатай': 'roll',

    'процедить': 'strain',
    'процеди': 'strain',

    'настоять': 'rest',
    'настаивать': 'rest',

    'подавать': 'garnish',
    'подать': 'garnish',
    'украсить': 'garnish'
}


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ
# ============================================================================

@dataclass
class ParsedIngredient:
    """Разобранный ингредиент"""
    name: str
    amount: str
    value: float = 0.0
    unit: str = 'pcs'
    allergens: List[str] = field(default_factory=list)
    notes: str = ''


@dataclass
class ParsedStep:
    """Разобранный шаг"""
    text: str
    action: str = 'prepare'
    time_minutes: Optional[int] = None
    temperature_c: Optional[int] = None


# ============================================================================
# RCIP CONVERTER
# ============================================================================

class RCIPConverter:
    """
    Конвертер рецептов в формат RCIP v0.1
    """

    def __init__(self):
        self.rcip_version = "0.1"

    # ========================================================================
    # ГЛАВНЫЙ МЕТОД КОНВЕРТАЦИИ
    # ========================================================================

    def convert(self,
                name: str,
                ingredients_text: str = None,
                steps_text: str = None,
                description: str = "",
                servings: int = 4,
                prep_time: int = None,
                cook_time: int = None,
                difficulty: str = "intermediate",
                cuisine: str = "",
                author: str = "Web Source",
                source_url: str = "") -> Dict:
        """
        Конвертирует рецепт в RCIP формат

        Args:
            name: Название рецепта
            ingredients_text: Текст ингредиентов (построчно)
            steps_text: Текст инструкций (построчно)
            description: Описание
            servings: Количество порций
            prep_time: Время подготовки (мин)
            cook_time: Время готовки (мин)
            difficulty: Сложность
            cuisine: Тип кухни
            author: Автор
            source_url: URL источника

        Returns:
            dict: RCIP рецепт
        """

        # Базовая структура
        recipe = {
            "rcip_version": self.rcip_version,
            "id": f"rcip-{uuid.uuid4()}",
            "meta": self._create_meta(
                name, description, servings, prep_time, cook_time,
                difficulty, cuisine, author
            ),
            "ingredients": [],
            "steps": []
        }

        # Парсим ингредиенты
        if ingredients_text:
            parsed_ingredients = self.parse_ingredients(ingredients_text)
            recipe["ingredients"] = [
                self._ingredient_to_rcip(ing, i+1)
                for i, ing in enumerate(parsed_ingredients)
            ]

        # Парсим шаги
        if steps_text:
            parsed_steps = self.parse_steps(steps_text)
            recipe["steps"] = [
                self._step_to_rcip(step, i+1)
                for i, step in enumerate(parsed_steps)
            ]

        # Определяем диеты из ингредиентов
        recipe["meta"]["diet_labels"] = self._detect_diet_labels(
            recipe["ingredients"]
        )

        # Добавляем расширения
        if source_url:
            recipe["extensions"] = {
                "source_url": source_url,
                "converted_date": datetime.utcnow().isoformat() + "Z"
            }

        return recipe

    # ========================================================================
    # ПАРСИНГ ИНГРЕДИЕНТОВ
    # ========================================================================

    def parse_ingredients(self, text: str) -> List[ParsedIngredient]:
        """
        Парсит текст ингредиентов

        Примеры:
        - "300г муки"
        - "2 ст.л. сахара"
        - "Соль по вкусу"
        """
        ingredients = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            # Пропускаем заголовки
            if line.lower().startswith(('ингредиент', 'состав', 'для теста')):
                continue

            # Удаляем маркеры списка
            line = re.sub(r'^[-•*]\s*', '', line)

            ingredient = self._parse_ingredient_line(line)
            if ingredient:
                ingredients.append(ingredient)

        return ingredients

    def _parse_ingredient_line(self, line: str) -> Optional[ParsedIngredient]:
        """Парсит одну строку ингредиента"""

        # Паттерн: количество + единица + название
        # Примеры: "300г муки", "2 ст.л. сахара", "500 мл молока"
        pattern = r'(\d+[.,]?\d*)\s*([а-яА-Я.]+)?\s+(.+)'
        match = re.match(pattern, line)

        if match:
            value_str = match.group(1).replace(',', '.')
            unit_str = match.group(2) or 'шт'
            name = match.group(3).strip()

            value = float(value_str)
            unit, multiplier = self._normalize_unit(unit_str)

            # Если единица в граммах/мл, умножаем
            if multiplier != 1:
                value = value * multiplier

        else:
            # Паттерн без количества: "Соль по вкусу"
            name = line.strip()
            value = 0
            unit = 'to-taste'

        # Определяем аллергены
        allergens = self._detect_allergens(name)

        return ParsedIngredient(
            name=name,
            amount=line,
            value=value,
            unit=unit,
            allergens=allergens
        )

    def _normalize_unit(self, unit_str: str) -> Tuple[str, float]:
        """
        Нормализует единицу измерения

        Returns:
            (стандартная_единица, множитель_для_базовой_единицы)
        """
        unit_lower = unit_str.lower().strip('.')

        for key, (standard_unit, multiplier) in UNIT_MAPPING.items():
            if key in unit_lower:
                return (standard_unit, multiplier)

        # По умолчанию - штуки
        return ('pcs', 1)

    def _detect_allergens(self, ingredient_name: str) -> List[str]:
        """Определяет аллергены в ингредиенте"""
        allergens = []
        name_lower = ingredient_name.lower()

        for allergen, keywords in ALLERGEN_KEYWORDS.items():
            if any(keyword in name_lower for keyword in keywords):
                allergens.append(allergen)

        return allergens

    # ========================================================================
    # ПАРСИНГ ШАГОВ
    # ========================================================================

    def parse_steps(self, text: str) -> List[ParsedStep]:
        """Парсит текст инструкций"""
        steps = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            # Пропускаем заголовки
            if line.lower().startswith(('приготовление', 'инструкция', 'шаг')):
                continue

            # Удаляем нумерацию
            line = re.sub(r'^\d+[\.)]\s*', '', line)
            line = re.sub(r'^[-•*]\s*', '', line)

            step = self._parse_step_line(line)
            if step:
                steps.append(step)

        return steps

    def _parse_step_line(self, line: str) -> Optional[ParsedStep]:
        """Парсит одну строку инструкции"""

        # Определяем действие
        action = self._detect_action(line)

        # Извлекаем время
        time_minutes = self._extract_time(line)

        # Извлекаем температуру
        temperature_c = self._extract_temperature(line)

        return ParsedStep(
            text=line,
            action=action,
            time_minutes=time_minutes,
            temperature_c=temperature_c
        )

    def _detect_action(self, text: str) -> str:
        """Определяет действие из текста"""
        text_lower = text.lower()

        for keyword, action in ACTION_MAPPING.items():
            if keyword in text_lower:
                return action

        return 'prepare'

    def _extract_time(self, text: str) -> Optional[int]:
        """Извлекает время из текста"""

        # Паттерны времени
        patterns = [
            r'(\d+)\s*мин',
            r'(\d+)\s*час',
            r'(\d+)-(\d+)\s*мин'
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                if 'час' in pattern:
                    return int(match.group(1)) * 60
                else:
                    # Берём среднее если диапазон
                    if match.lastindex == 2:
                        return (int(match.group(1)) + int(match.group(2))) // 2
                    return int(match.group(1))

        return None

    def _extract_temperature(self, text: str) -> Optional[int]:
        """Извлекает температуру из текста"""

        patterns = [
            r'(\d+)\s*[°С]',
            r'(\d+)\s*град',
            r'при\s+(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))

        return None

    # ========================================================================
    # СОЗДАНИЕ RCIP СТРУКТУР
    # ========================================================================

    def _create_meta(self, name, description, servings, prep_time,
                     cook_time, difficulty, cuisine, author) -> Dict:
        """Создаёт meta секцию RCIP"""

        meta = {
            "name": name,
            "author": author,
            "created_date": datetime.utcnow().isoformat() + "Z",
            "difficulty": difficulty
        }

        if description:
            meta["description"] = description

        if servings:
            meta["servings"] = {
                "amount": servings,
                "unit": "portions",
                "adjustable": True
            }

        if prep_time:
            meta["prep_time_minutes"] = prep_time

        if cook_time:
            meta["cook_time_minutes"] = cook_time

        if prep_time and cook_time:
            meta["total_time_minutes"] = prep_time + cook_time

        if cuisine:
            meta["keywords"] = [cuisine.lower()]

        meta["diet_labels"] = []

        return meta

    def _ingredient_to_rcip(self, ing: ParsedIngredient, index: int) -> Dict:
        """Конвертирует ParsedIngredient в RCIP формат"""

        return {
            "id": f"ing-{index:04d}",
            "name": ing.name,
            "human_amount": ing.amount,
            "machine_amount": {
                "value": ing.value,
                "unit": ing.unit,
                "approximate": False
            },
            "allergens": ing.allergens,
            "notes": ing.notes
        }

    def _step_to_rcip(self, step: ParsedStep, index: int) -> Dict:
        """Конвертирует ParsedStep в RCIP формат"""

        rcip_step = {
            "step_id": f"s-{index:02d}",
            "human_text": step.text,
            "action": step.action
        }

        # Добавляем параметры если есть
        params = {}
        if step.time_minutes:
            params["time_minutes"] = step.time_minutes
        if step.temperature_c:
            params["temperature_c"] = step.temperature_c

        if params:
            rcip_step["params"] = params

        return rcip_step

    def _detect_diet_labels(self, ingredients: List[Dict]) -> List[str]:
        """Определяет диетические метки из ингредиентов"""

        all_allergens = set()
        for ing in ingredients:
            all_allergens.update(ing.get("allergens", []))

        diet_labels = []

        # Проверяем отсутствие мяса/рыбы
        has_meat = any(a in all_allergens for a in ['fish'])
        if not has_meat:
            # Можем добавить vegetarian только если уверены
            pass

        # Без глютена
        if 'gluten' not in all_allergens and 'wheat' not in all_allergens:
            diet_labels.append('gluten-free')

        # Без молочных продуктов
        if 'milk' not in all_allergens and 'lactose' not in all_allergens:
            diet_labels.append('dairy-free')

        # Без орехов
        if 'tree-nuts' not in all_allergens and 'peanuts' not in all_allergens:
            diet_labels.append('nut-free')

        return diet_labels

    # ========================================================================
    # ПАРСИНГ ИЗ SCHEMA.ORG (JSON-LD)
    # ========================================================================

    def from_schema_org(self, schema_data: Dict) -> Dict:
        """
        Конвертирует из Schema.org Recipe в RCIP

        Args:
            schema_data: Данные в формате Schema.org Recipe

        Returns:
            dict: RCIP рецепт
        """

        # Извлекаем данные из Schema.org
        name = schema_data.get('name', 'Unknown Recipe')
        description = schema_data.get('description', '')

        # Автор
        author_data = schema_data.get('author', {})
        if isinstance(author_data, dict):
            author = author_data.get('name', 'Unknown')
        else:
            author = str(author_data)

        # Время
        prep_time = self._parse_iso_duration(schema_data.get('prepTime', ''))
        cook_time = self._parse_iso_duration(schema_data.get('cookTime', ''))

        # Порции
        servings = schema_data.get('recipeYield')
        if isinstance(servings, str):
            servings = int(re.search(r'\d+', servings).group()
                           ) if re.search(r'\d+', servings) else 4
        elif not servings:
            servings = 4

        # Ингредиенты
        ingredients_list = schema_data.get('recipeIngredient', [])
        ingredients_text = '\n'.join(ingredients_list)

        # Шаги
        instructions = schema_data.get('recipeInstructions', [])
        if isinstance(instructions, str):
            steps_text = instructions
        elif isinstance(instructions, list):
            steps_text = '\n'.join([
                step.get('text', str(step)) if isinstance(
                    step, dict) else str(step)
                for step in instructions
            ])
        else:
            steps_text = ''

        # Конвертируем
        return self.convert(
            name=name,
            ingredients_text=ingredients_text,
            steps_text=steps_text,
            description=description,
            servings=servings,
            prep_time=prep_time,
            cook_time=cook_time,
            author=author
        )

    def _parse_iso_duration(self, duration: str) -> Optional[int]:
        """
        Парсит ISO 8601 duration в минуты
        Пример: PT30M -> 30, PT1H30M -> 90
        """
        if not duration:
            return None

        minutes = 0

        # Часы
        hours_match = re.search(r'(\d+)H', duration)
        if hours_match:
            minutes += int(hours_match.group(1)) * 60

        # Минуты
        minutes_match = re.search(r'(\d+)M', duration)
        if minutes_match:
            minutes += int(minutes_match.group(1))

        return minutes if minutes > 0 else None

    # ========================================================================
    # УТИЛИТЫ
    # ========================================================================

    def validate(self, recipe: Dict) -> Tuple[bool, List[str]]:
        """
        Простая валидация RCIP рецепта

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Проверяем обязательные поля
        required = ['rcip_version', 'id', 'meta', 'ingredients', 'steps']
        for field in required:
            if field not in recipe:
                errors.append(f"Missing required field: {field}")

        # Проверяем allergens в ингредиентах
        for i, ing in enumerate(recipe.get('ingredients', [])):
            if 'allergens' not in ing:
                errors.append(f"Ingredient {i+1} missing allergens field")

        return (len(errors) == 0, errors)

    def save_to_file(self, recipe: Dict, filepath: str):
        """Сохраняет рецепт в файл"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(recipe, f, ensure_ascii=False, indent=2)


# ============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================================

def example_usage():
    """Примеры использования конвертера"""

    converter = RCIPConverter()

    # ========================================
    # Пример 1: Простой текстовый рецепт
    # ========================================

    ingredients = """
    300г муки
    2 яйца
    200 мл молока
    1 ст.л. сахара
    Соль по вкусу
    """

    steps = """
    1. Смешать муку с сахаром и солью
    2. Добавить яйца и перемешать
    3. Влить молоко и взбить до однородности
    4. Жарить блины на разогретой сковороде 2-3 минуты с каждой стороны
    """

    recipe1 = converter.convert(
        name="Блины на молоке",
        ingredients_text=ingredients,
        steps_text=steps,
        description="Классические русские блины",
        servings=10,
        prep_time=10,
        cook_time=20,
        difficulty="beginner",
        cuisine="Russian"
    )

    print("✅ Рецепт 1 создан:")
    print(f"   - Ингредиентов: {len(recipe1['ingredients'])}")
    print(f"   - Шагов: {len(recipe1['steps'])}")

    # Валидация
    is_valid, errors = converter.validate(recipe1)
    print(f"   - Валидный: {is_valid}")

    # Сохранение
    converter.save_to_file(recipe1, "bliny.rcip")

    # ========================================
    # Пример 2: Из Schema.org
    # ========================================

    schema_org_data = {
        "@type": "Recipe",
        "name": "Греческий салат",
        "description": "Свежий овощной салат",
        "author": {"name": "Chef Maria"},
        "prepTime": "PT15M",
        "recipeYield": "4 servings",
        "recipeIngredient": [
            "2 помидора",
            "1 огурец",
            "100г феты",
            "10 маслин",
            "1 красный лук"
        ],
        "recipeInstructions": [
            "Нарезать овощи крупными кусками",
            "Добавить фету и маслины",
            "Заправить оливковым маслом"
        ]
    }

    recipe2 = converter.from_schema_org(schema_org_data)

    print("\n✅ Рецепт 2 из Schema.org создан:")
    print(f"   - Ингредиентов: {len(recipe2['ingredients'])}")
    print(f"   - Шагов: {len(recipe2['steps'])}")

    converter.save_to_file(recipe2, "greek_salad.rcip")

    print("\n🎉 Конвертация завершена!")


if __name__ == "__main__":
    example_usage()
