class_name BaseEntity
extends Node2D

var health: int = 100

func take_damage(amount: int) -> void:
    health -= amount
