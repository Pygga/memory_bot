# UML-диаграммы

| Файл | Тип | Описание |
|------|-----|----------|
| `use_case.puml` | Прецедентов | Акторы и сценарии использования |
| `class_diagram.puml` | Классов | Модели БД и AI-компоненты |
| `component_diagram.puml` | Компонентов | Внутренняя архитектура бота |
| `deployment_diagram.puml` | Развёртывания | Инфраструктура (Railway, Groq, Telegram) |

## Как открыть

**Онлайн:** вставь содержимое `.puml` файла на https://www.plantuml.com/plantuml/uml/

**VS Code:** установи расширение _PlantUML_ (jebbs.plantuml), открой `.puml` и нажми `Alt+D`.

**Python (локально):**
```bash
pip install plantuml
python -c "
import plantuml
p = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')
p.processes_file('use_case.puml')
"
```
