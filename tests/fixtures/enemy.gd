class_name Enemy
extends "res://base_entity.gd"

var damage: int = 10
var target: Player

func attack() -> void:
    if target:
        target.take_damage(damage)
