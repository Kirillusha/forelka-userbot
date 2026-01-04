# Документация по модулям Forelka Userbot

## 📚 Структура модуля

Каждый модуль для Forelka должен иметь следующую структуру:

```python
from pyrogram.enums import ParseMode

async def my_command_cmd(client, message, args):
    """
    Основная функция команды
    
    Args:
        client: Pyrogram Client instance
        message: Message object
        args: List of command arguments
    """
    # Ваш код здесь
    await message.edit("Hello from my module!", parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    """
    Регистрация команды в системе
    
    Args:
        app: Client instance
        commands: Dictionary of all commands
        module_name: Name of this module
    """
    commands["mycommand"] = {"func": my_command_cmd, "module": module_name}
```

## 🎯 Основные правила

1. **Имя функции команды**: должно заканчиваться на `_cmd`
2. **Функция register**: обязательна для каждого модуля
3. **Параметры**: все команды получают `(client, message, args)`
4. **Форматирование**: используйте `ParseMode.HTML` для красивых сообщений
5. **Эмодзи**: используйте Telegram emoji IDs для кастомных эмодзи

## 📦 Создание репозитория модулей

Вы можете создать свой репозиторий с модулями. Структура может быть любой:

### Вариант 1: Все модули в корне
```
my-modules-repo/
├── ping.py
├── userinfo.py
├── weather.py
└── README.md
```

### Вариант 2: Модули в подпапке
```
my-modules-repo/
├── modules/
│   ├── ping.py
│   ├── userinfo.py
│   └── weather.py
├── README.md
└── requirements.txt
```

### Вариант 3: Сложная структура
```
my-modules-repo/
├── fun/
│   ├── memes.py
│   └── jokes.py
├── utils/
│   ├── calc.py
│   └── convert.py
└── README.md
```

Forelka автоматически найдет все `.py` файлы в репозитории и загрузит их!

## 🚀 Использование эмодзи в модулях

Telegram поддерживает кастомные эмодзи через ID. Примеры часто используемых:

```python
# Успех
<emoji id=5776375003280838798>✅</emoji>

# Ошибка
<emoji id=5778527486270770928>❌</emoji>

# Загрузка
<emoji id=5891211339170326418>⌛️</emoji>

# Информация
<emoji id=5775887550262546277>❗️</emoji>

# Стрелка
<emoji id=5877468380125990242>➡️</emoji>

# Призрак (логотип Forelka)
<emoji id=5897962422169243693>👻</emoji>
```

## 📝 Примеры модулей

### Простой модуль без аргументов

```python
from pyrogram.enums import ParseMode

async def hello_cmd(client, message, args):
    await message.edit(
        "<blockquote><emoji id=5897962422169243693>👻</emoji> <b>Hello from Forelka!</b></blockquote>",
        parse_mode=ParseMode.HTML
    )

def register(app, commands, module_name):
    commands["hello"] = {"func": hello_cmd, "module": module_name}
```

### Модуль с аргументами

```python
from pyrogram.enums import ParseMode

async def say_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .say [text]</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    text = " ".join(args)
    await message.edit(f"<blockquote>💬 {text}</blockquote>", parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["say"] = {"func": say_cmd, "module": module_name}
```

### Модуль с несколькими командами

```python
from pyrogram.enums import ParseMode
import random

async def roll_cmd(client, message, args):
    number = random.randint(1, 6)
    await message.edit(
        f"<blockquote>🎲 <b>Dice rolled:</b> <code>{number}</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

async def flip_cmd(client, message, args):
    result = random.choice(["Heads", "Tails"])
    await message.edit(
        f"<blockquote>🪙 <b>Coin flipped:</b> <code>{result}</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

def register(app, commands, module_name):
    commands["roll"] = {"func": roll_cmd, "module": module_name}
    commands["flip"] = {"func": flip_cmd, "module": module_name}
```

## 🔧 Работа с внешними библиотеками

Если ваш модуль требует дополнительных библиотек, добавьте `requirements.txt` в корень репозитория:

```
requests>=2.31.0
beautifulsoup4>=4.12.0
pillow>=10.0.0
```

Пользователи смогут установить зависимости командой:
```bash
pip install -r requirements.txt
```

## 🎨 Форматирование сообщений

Используйте HTML-теги для форматирования:

```python
# Жирный текст
<b>Bold text</b>

# Курсив
<i>Italic text</i>

# Код
<code>Code block</code>

# Цитата (блокквот)
<blockquote>Quote text</blockquote>

# Раскрывающаяся цитата
<blockquote expandable>Long text that can be expanded</blockquote>

# Моноширинный (предформатированный)
<pre>Preformatted text</pre>

# Ссылка
<a href="https://example.com">Link text</a>
```

## 🔐 Защищенные модули

Следующие имена модулей защищены и не могут быть перезаписаны:
- `loader` - система загрузки модулей
- `main` - основной файл
- Любые модули из папки `modules/` (системные модули)

## 📋 Команды для работы с модулями

### Загрузка из URL
```
.dlm <url> <name> - Загрузить модуль по прямой ссылке
```

### Загрузка из файла
```
.lm - Ответить на файл .py для загрузки
.lm [name] - Загрузить с кастомным именем
```

### Загрузка из репозитория
```
.dlmr <repo_url> - Загрузить все модули из репозитория
.dlmr <repo_url> <module_name> - Загрузить конкретный модуль
```

### Управление модулями
```
.lm - Показать список загруженных модулей
.ulm <name> - Удалить модуль
.ml <name> - Отправить модуль как файл
```

### Управление репозиториями
```
.lmr - Показать список загруженных репозиториев
.rmr <repo_name> - Удалить репозиторий
```

## 🌟 Примеры репозиториев

Создайте свой репозиторий на GitHub с модулями и поделитесь им с сообществом!

Пример структуры README для репозитория модулей:

```markdown
# My Forelka Modules

Collection of custom modules for Forelka Userbot

## Installation

```
.dlmr https://github.com/username/my-forelka-modules
```

## Modules

- **weather** - Get weather information
- **meme** - Random meme generator
- **calc** - Advanced calculator

## Requirements

```bash
pip install -r requirements.txt
```
```

## 💡 Советы по разработке

1. **Тестируйте модули** перед публикацией
2. **Обрабатывайте ошибки** с помощью try/except
3. **Документируйте код** - добавляйте docstrings
4. **Используйте async/await** для асинхронных операций
5. **Не блокируйте главный поток** - используйте asyncio
6. **Добавляйте help-сообщения** для всех команд
7. **Версионируйте ваши модули** через git tags

## 🤝 Поддержка

- Канал: https://t.me/forelkauserbots
- Поддержка: https://t.me/forelusersupport

---

Создано для Forelka Userbot 👻
