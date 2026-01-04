MOVE_UNTIL_OBSTACLE
Робот движется вперёд, пока не обнаружит препятствие впереди, затем останавливается.

Parameters
Name	Type	Required	Default	Description speed	float	no	0.5	Линейная скорость движения
distance_threshold	float	no	0.3	Минимальная дистанция до препятствия (м) Behaviour (High-Level) робот движется вперёд постоянно проверяет состояние мира при обнаружении препятствия ближе порога — останавливается

Example Commands
“Move forward until you see an obstacle”
“Go ahead and stop before the wall”
“Drive straight until something blocks the way”

STOP_AT_DISTANCE
Робот движется вперёд и останавливается на заданной дистанции от препятствия.

Parameters
Name	Type	Required	Default	Description
speed	float	no	0.5	Линейная скорость
target_distance	float	yes	—	Целевая дистанция до препятствия (м)
Behaviour (High-Level)

робот движется вперёд и останавливается, когда расстояние до препятствия равно или меньше заданного

Example Commands
“Stop at 30 centimeters from the wall”
“Move forward and stop half a meter before the obstacle”

CONDITIONAL_TURN
Робот выполняет поворот в зависимости от логического условия окружения.

Parameters
Name	Type	Required	Default	Description
condition	enum	yes	—	Условие (front_blocked, left_blocked, right_blocked)
direction	enum	yes	—	Направление поворота (left, right)
angular_speed	float	no	0.5	Скорость поворота
Behaviour (High-Level)

робот проверяет условие если условие истинно — выполняет поворот иначе — не выполняет действия

Example Commands
“If there is a wall on the right, turn left”
“Turn right if the front is blocked”