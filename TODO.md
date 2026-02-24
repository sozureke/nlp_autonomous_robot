## PRIORITY 2 — LLM Intent Layer (Semantic Compiler)

- [x] Создать `llm_agent.py`
- [x] Описать JSON‑схему внешнего интента (action / speed / until / …)
- [x] Настроить prompt так, чтобы LLM возвращал строго валидный JSON по схеме
- [x] Добавить валидацию JSON (pydantic/jsonschema)
- [x] Реализовать fallback‑парсер (rule‑based) на случай ошибок LLM

## PRIORITY 3 — Robot Executive Layer

- [x] Создать `robot_executor/executor.py`
- [x] Реализовать маппинг `intent → sequence of actions`
- [x] Интегрировать executor с уже существующим `Planner` (или эволюционно заменить его)
- [x] Гарантировать, что только executor вызывает `RobotActions` / `BaseRobot`

## PRIORITY 4 — World State

- [x] Расширить `WorldModel` до общего `world_state`
- [x] Добавить метод экспорта в dict/JSON для LLM
- [x] Включить в состояние:
  - [x] данные ультразвука / ИК
  - [x] derived‑флаги (`obstacle`, `path_clear`, …)
  - [x] внутреннее состояние робота (`moving`, последний action и т.п.)

## PRIORITY 5 — Memory

- [x] Создать `memory/short_term_memory.py`
- [x] Реализовать хранение последних событий/объектов
- [x] Добавить экспорт памяти в dict для LLM
- [ ] Интегрировать запись событий из executor’а и perception

## PRIORITY 6 — Camera Integration

- [ ] Настроить подключение Raspberry Pi → ESP32‑CAM stream
- [ ] Создать `vision_node/`
- [ ] Определить простой JSON‑выход vision‑узла:
  - [ ] `object_visible`
  - [ ] `object_type`
  - [ ] `path_free`
- [ ] Не пускать bbox/сырые пиксели выше perception‑слоя

## PRIORITY 7 — Sensor Fusion

- [ ] Создать `perception/fusion.py`
- [ ] Объединить ultrasonic + vision в единый `world_state`
- [ ] Определить стратегию разрешения конфликтов (vision vs ultrasonic)

## PRIORITY 8 — LLM Context Awareness

- [ ] Расширить контекст LLM до:
  - [ ] `command`
  - [ ] `world_state`
  - [ ] `memory`
- [ ] Обновить prompt LLM под новый контекст

## PRIORITY 9 — Safety Layer

- [ ] Создать `safety_controller.py`
- [ ] Определить набор safety‑правил (макс. скорость, дистанции, запрет опасных последовательностей)
- [ ] Встроить safety‑check перед любым исполнением action/intent
- [ ] Гарантировать, что при нарушении правил команда блокируется или деградирует в безопасную
