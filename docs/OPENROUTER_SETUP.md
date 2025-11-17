# 🤖 OpenRouter Setup Guide

Этот гайд объясняет, как настроить AI Friends Bot с бесплатной моделью **Gemini 2.0 Flash** через OpenRouter.

---

## 🎯 Зачем OpenRouter?

**Преимущества для MVP/тестирования:**

✅ **Бесплатно** - модель `google/gemini-2.0-flash-exp:free` не требует оплаты
✅ **Без депозита** - не нужна кредитная карта
✅ **Быстрый старт** - регистрация за 1 минуту
✅ **Единый API** - доступ ко множеству моделей через один интерфейс
✅ **OpenAI-совместимый** - используем библиотеку `openai`

---

## 📝 Регистрация на OpenRouter

### Шаг 1: Создайте аккаунт

1. Перейдите на [openrouter.ai](https://openrouter.ai)
2. Нажмите **"Sign In"** в правом верхнем углу
3. Выберите способ входа:
   - Google
   - GitHub
   - Discord
   - Email

### Шаг 2: Создайте API ключ

1. После входа перейдите в раздел **"Keys"** (или [openrouter.ai/keys](https://openrouter.ai/keys))
2. Нажмите **"Create Key"**
3. (Опционально) Дайте ключу имя, например: "AI Friends Bot Test"
4. Скопируйте ключ

**Важно**: Ключ выглядит так: `sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Шаг 3: Добавьте ключ в `.env`

Откройте файл `.env` и добавьте:

```env
OPENROUTER_API_KEY=sk-or-v1-ваш-реальный-ключ
LLM_MODEL=google/gemini-2.0-flash-exp:free
```

---

## 🆓 Бесплатные модели на OpenRouter

| Модель | Описание | Лимиты |
|--------|----------|--------|
| **google/gemini-2.0-flash-exp:free** | Gemini 2.0 Flash (рекомендуется) | Общий лимит на все пользователи |
| **google/gemini-flash-1.5:free** | Gemini 1.5 Flash | Общий лимит |
| **meta-llama/llama-3.2-3b-instruct:free** | LLaMA 3.2 3B | Общий лимит |

**По умолчанию используется**: `google/gemini-2.0-flash-exp:free`

### Как сменить модель?

В файле `.env` измените:

```env
LLM_MODEL=другая-модель
```

Например:

```env
LLM_MODEL=google/gemini-flash-1.5:free
```

---

## 💰 Платные модели (опционально)

Если нужна более мощная модель, OpenRouter поддерживает:

- **GPT-4 Turbo** (`openai/gpt-4-turbo`)
- **Claude 3.5 Sonnet** (`anthropic/claude-3.5-sonnet`)
- **Gemini 1.5 Pro** (`google/gemini-pro-1.5`)

Для платных моделей:
1. Пополните баланс на [openrouter.ai/credits](https://openrouter.ai/credits)
2. Измените `LLM_MODEL` в `.env`

**Цены**: См. [openrouter.ai/models](https://openrouter.ai/models)

---

## 🔧 Техническая информация

### Как это работает?

OpenRouter предоставляет **OpenAI-совместимый API**:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-or-...",
    base_url="https://openrouter.ai/api/v1"
)

response = await client.chat.completions.create(
    model="google/gemini-2.0-flash-exp:free",
    messages=[{"role": "user", "content": "Привет!"}]
)
```

### Преимущества этого подхода:

✅ Не нужна отдельная библиотека для каждого провайдера
✅ Легко переключаться между моделями (меняя только `model`)
✅ Стандартизированный формат запросов/ответов

---

## ⚡ Производительность

### Gemini 2.0 Flash (free)

- **Скорость**: 2-5 секунд на ответ
- **Качество**: Отлично для диалогов на русском языке
- **Tone of Voice**: Хорошо следует system prompt "подружки"
- **Context window**: 1M токенов

### Рекомендации:

✅ **Для тестирования MVP** - идеально
✅ **Для Closed Beta** (100 пользователей) - подходит
⚠️ **Для Production** - рассмотреть платную модель (Claude 3.5 Sonnet)

---

## 🛡️ Безопасность

### Что НЕ делать:

❌ Не коммитьте `.env` в git (уже в `.gitignore`)
❌ Не делитесь ключом API публично
❌ Не храните ключ в коде (только в `.env`)

### Что делать:

✅ Храните ключ только в `.env`
✅ Используйте `.env.example` как шаблон
✅ Регулярно ротируйте ключи (создавайте новые на OpenRouter)

---

## 🐛 Troubleshooting

### Ошибка: "Invalid API key"

**Решение**:
1. Проверьте, что ключ скопирован полностью (начинается с `sk-or-v1-`)
2. Проверьте, что в `.env` нет лишних пробелов
3. Убедитесь, что `.env` находится в корне проекта

### Ошибка: "Model not found"

**Решение**:
1. Проверьте правильность имени модели (регистр важен!)
2. Проверьте, что модель доступна: [openrouter.ai/models](https://openrouter.ai/models)
3. Для бесплатных моделей добавьте суффикс `:free`

### Бот отвечает очень медленно (>10 секунд)

**Возможные причины**:
- Высокая нагрузка на бесплатную модель
- Проблемы с интернет-соединением
- Rate limiting

**Решение**:
1. Попробуйте другую бесплатную модель
2. Рассмотрите платную модель для лучшей производительности

### Ошибка: "Rate limit exceeded"

**Решение**:
- Бесплатные модели имеют общий лимит на всех пользователей
- Подождите 1-2 минуты и попробуйте снова
- Рассмотрите платную модель для guaranteed QPS

---

## 📊 Мониторинг использования

### Посмотреть статистику:

1. Перейдите на [openrouter.ai/activity](https://openrouter.ai/activity)
2. Вы увидите:
   - Количество запросов
   - Использованные токены
   - Потраченные средства (для платных моделей)

### Установить лимиты:

1. Перейдите в [openrouter.ai/settings](https://openrouter.ai/settings)
2. Установите **"Credit Limit"** (максимальная сумма расходов)

---

## 🔄 Миграция на другого провайдера

### Anthropic Claude (Phase 2)

Если решите мигрировать на прямую интеграцию с Claude:

1. Получите ключ на [console.anthropic.com](https://console.anthropic.com)
2. Раскомментируйте в `requirements.txt`:
   ```
   anthropic==0.18.1
   ```
3. Установите: `pip install anthropic==0.18.1`
4. Обновите `src/services/ai_service.py` для использования Anthropic SDK

### OpenAI GPT-4

Если нужен прямой доступ к OpenAI:

1. Получите ключ на [platform.openai.com](https://platform.openai.com)
2. В `.env` измените:
   ```env
   OPENROUTER_API_KEY=sk-...  # OpenAI ключ
   LLM_MODEL=gpt-4-turbo
   ```
3. В `src/services/ai_service.py` измените `base_url`:
   ```python
   base_url="https://api.openai.com/v1"
   ```

---

## 📚 Дополнительные ресурсы

- **OpenRouter Docs**: [openrouter.ai/docs](https://openrouter.ai/docs)
- **Список моделей**: [openrouter.ai/models](https://openrouter.ai/models)
- **Цены**: [openrouter.ai/models](https://openrouter.ai/models) (столбец "Pricing")
- **Discord**: [discord.gg/openrouter](https://discord.gg/openrouter)

---

## ✅ Чеклист готовности

Перед запуском убедитесь:

- [ ] Зарегистрирован аккаунт на OpenRouter
- [ ] Создан API ключ
- [ ] Ключ добавлен в `.env`
- [ ] Модель указана: `google/gemini-2.0-flash-exp:free`
- [ ] Файл `.env` НЕ в git (проверьте `.gitignore`)
- [ ] Зависимости установлены: `pip install -r requirements.txt`

**Готово? Запустите бота:**

```bash
python -m src.main
```

---

**Версия**: 1.0
**Последнее обновление**: Ноябрь 2024
