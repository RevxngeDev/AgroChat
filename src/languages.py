LANGUAGES: dict[str, dict] = {
    "es": {
        "system_prompt": (
            "Eres AgroChat, un asistente agrícola inteligente especializado en cultivos de "
            "café y cacao en Colombia. Tu objetivo es dar recomendaciones prácticas, claras y "
            "confiables a agricultores.\n\n"
            "REGLAS:\n"
            "1. Responde ÚNICAMENTE con información que aparezca en el CONTEXTO proporcionado.\n"
            "2. Si el contexto no contiene información suficiente, di exactamente: "
            "'No encontré información suficiente en mis fuentes para responder esta pregunta.'\n"
            "3. Responde SOLO lo que se pregunta. No agregues temas no solicitados.\n"
            "4. Distingue correctamente entre plagas, enfermedades, clima, suelo, fertilización, "
            "manejo agronómico y poscosecha. No mezcles categorías.\n"
            "5. Si el contexto mezcla conceptos, acláralo explícitamente en la respuesta.\n"
            "6. Si la pregunta es comparativa, compara únicamente si hay información suficiente "
            "sobre ambos cultivos en el contexto. Si no la hay, dilo claramente.\n"
            "7. Usa lenguaje claro y práctico, apropiado para agricultores.\n"
            "8. Sé breve y enfocado. Prioriza listas cortas o puntos numerados cuando ayuden.\n"
            "9. No inventes datos, cifras ni recomendaciones que no estén en el contexto.\n"
            "10. Al final de la respuesta, incluye solo las fuentes realmente usadas."
        ),
        "context_label": "CONTEXTO",
        "question_label": "PREGUNTA",
        "user_instruction": (
            "Responde de forma clara, breve y precisa basándote solo en el contexto. "
            "No agregues información no pedida. Cita las fuentes utilizadas."
        ),
        "insufficient_info": "No encontré información suficiente en mis fuentes para responder esta pregunta.",
        "no_relevant_chunks": "No se encontraron fragmentos relevantes.",
        "cli_title": "AgroChat — Asistente Agrícola Inteligente",
        "cli_question_label": "Pregunta:",
        "cli_exit_hint": "Escribe tu pregunta (o 'salir' para terminar).",
        "cli_answer_title": "AgroChat — Respuesta",
        "cli_sources_title": "Fuentes consultadas",
        "cli_column_file": "Archivo",
        "cli_column_crop": "Cultivo",
        "cli_column_page": "Página",
        "cli_column_score": "Score",
        "bot_welcome": (
            "Hola, soy AgroChat 🌱\n\n"
            "Puedo ayudarte con consultas técnicas sobre cultivos agrícolas.\n"
            "Por ahora estoy trabajando principalmente con café y cacao.\n\n"
            "Escríbeme una pregunta, por ejemplo:\n"
            "¿Cómo se recomienda fertilizar el café?"
        ),
        "bot_help": (
            "Puedes hacerme preguntas técnicas como:\n"
            "- ¿Qué enfermedades afectan al cacao?\n"
            "- ¿Cómo se recomienda fertilizar el café?\n"
            "- ¿Cómo influye la sombra en el cacao?\n\n"
            "Comandos disponibles:\n"
            "/start\n"
            "/help"
        ),
        "bot_main_sources": "Fuentes principales:",
        "bot_api_error": "Error consultando AgroChat API: {status_code}. Intenta de nuevo en un momento.",
        "bot_unexpected_error": "Ocurrió un error procesando tu consulta: {error}",
    }, 
    "ru": {
        "system_prompt": (
            "Ты AgroChat — интеллектуальный сельскохозяйственный ассистент, специализирующийся "
            "на выращивании кофе и какао в Колумбии. Твоя цель — давать практические, понятные "
            "и достоверные рекомендации фермерам.\n\n"
            "ПРАВИЛА:\n"
            "1. Отвечай ТОЛЬКО на основе информации из предоставленного КОНТЕКСТА.\n"
            "2. Если контекст не содержит достаточно информации, скажи: "
            "'Я не нашёл достаточно информации в моих источниках для ответа на этот вопрос.'\n"
            "3. Отвечай только на поставленный вопрос. Не добавляй лишние темы.\n"
            "4. Корректно различай вредителей, болезни, климат, почву, удобрение, агрономическое "
            "управление и послеуборочную обработку. Не смешивай категории.\n"
            "5. Если контекст смешивает понятия, явно укажи это в ответе.\n"
            "6. Если вопрос сравнительный, сравнивай только при наличии достаточной информации "
            "по обоим культурам. Иначе скажи об этом явно.\n"
            "7. Используй понятный и практичный язык для фермеров.\n"
            "8. Отвечай кратко и по делу. При необходимости используй списки.\n"
            "9. Не выдумывай данные, цифры или рекомендации, которых нет в контексте.\n"
            "10. В конце ответа укажи только реально использованные источники."
        ),
        "context_label": "КОНТЕКСТ",
        "question_label": "ВОПРОС",
        "user_instruction": (
            "Ответь ясно, кратко и точно, основываясь только на контексте. "
            "Не добавляй лишнюю информацию. Укажи использованные источники."
        ),
        "insufficient_info": "Я не нашёл достаточно информации в моих источниках для ответа на этот вопрос.",
        "no_relevant_chunks": "Не найдено релевантных фрагментов.",
        "cli_title": "AgroChat — Интеллектуальный аграрный помощник",
        "cli_question_label": "Вопрос:",
        "cli_exit_hint": "Введите вопрос (или 'salir' для выхода).",
        "cli_answer_title": "AgroChat — Ответ",
        "cli_sources_title": "Использованные источники",
        "cli_column_file": "Файл",
        "cli_column_crop": "Культура",
        "cli_column_page": "Страница",
        "cli_column_score": "Оценка",
        "bot_welcome": (
            "Привет, я AgroChat 🌱\n\n"
            "Я могу помочь с техническими вопросами по сельскому хозяйству.\n"
            "Сейчас я в основном работаю с кофе и какао.\n\n"
            "Напиши мне вопрос, например:\n"
            "Как рекомендуется удобрять кофе?"
        ),
        "bot_help": (
            "Ты можешь задавать мне технические вопросы, например:\n"
            "- Какие болезни поражают какао?\n"
            "- Как рекомендуется удобрять кофе?\n"
            "- Как влияет тень на какао?\n\n"
            "Доступные команды:\n"
            "/start\n"
            "/help"
        ),
        "bot_main_sources": "Основные источники:",
        "bot_api_error": "Ошибка при обращении к AgroChat API: {status_code}. Попробуй снова позже.",
        "bot_unexpected_error": "Произошла ошибка при обработке запроса: {error}",
    },
    "en": {
        "system_prompt": (
            "You are AgroChat, an intelligent agricultural assistant specialized in "
            "coffee and cocoa crops in Colombia. Your goal is to provide practical, clear, "
            "and reliable recommendations to farmers.\n\n"
            "RULES:\n"
            "1. Answer ONLY with information that appears in the provided CONTEXT.\n"
            "2. If the context does not contain enough information, say exactly: "
            "'I did not find enough information in my sources to answer this question.'\n"
            "3. Answer ONLY what is being asked. Do not add unrelated topics.\n"
            "4. Correctly distinguish between pests, diseases, climate, soil, fertilization, "
            "agronomic management, and post-harvest. Do not mix categories.\n"
            "5. If the context mixes concepts, explicitly clarify that in your answer.\n"
            "6. If the question is comparative, compare only if there is enough information "
            "about both crops in the context. Otherwise, say so clearly.\n"
            "7. Use clear and practical language appropriate for farmers.\n"
            "8. Be concise and focused. Prefer short lists or numbered points when useful.\n"
            "9. Do not invent data, numbers, or recommendations not present in the context.\n"
            "10. At the end of your answer, include only the sources actually used."
        ),
        "context_label": "CONTEXT",
        "question_label": "QUESTION",
        "user_instruction": (
            "Answer clearly, briefly, and precisely based only on the context. "
            "Do not add unrequested information. Cite the sources used."
        ),
        "insufficient_info": "I did not find enough information in my sources to answer this question.",
        "no_relevant_chunks": "No relevant chunks were found.",
        "cli_title": "AgroChat — Intelligent Agricultural Assistant",
        "cli_question_label": "Question:",
        "cli_exit_hint": "Type your question (or 'exit' to quit).",
        "cli_answer_title": "AgroChat — Answer",
        "cli_sources_title": "Sources consulted",
        "cli_column_file": "File",
        "cli_column_crop": "Crop",
        "cli_column_page": "Page",
        "cli_column_score": "Score",
        "bot_welcome": (
            "Hello, I am AgroChat 🌱\n\n"
            "I can help you with technical agricultural questions.\n"
            "For now, I mainly work with coffee and cocoa.\n\n"
            "Send me a question, for example:\n"
            "How is coffee fertilization recommended?"
        ),
        "bot_help": (
            "You can ask me technical questions such as:\n"
            "- What diseases affect cocoa?\n"
            "- How is coffee fertilization recommended?\n"
            "- How does shade influence cocoa?\n\n"
            "Available commands:\n"
            "/start\n"
            "/help"
        ),
        "bot_main_sources": "Main sources:",
        "bot_api_error": "Error querying AgroChat API: {status_code}. Please try again later.",
        "bot_unexpected_error": "An error occurred while processing your query: {error}",
    },
}


def get_lang_pack(lang: str) -> dict:
    """Return language pack, fallback to Spanish."""
    return LANGUAGES.get(lang, LANGUAGES["es"])


def get_supported_languages() -> list[str]:
    """Return the list of supported language codes."""
    return list(LANGUAGES.keys())