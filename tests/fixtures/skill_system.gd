class_name SkillSystem
extends Node

const Trigger := {
    HEAL = 0,
    DAMAGE = 1,
}

var current_target: Player
var inventory_ref: Inventory = null

func apply(target: Player, source: BaseEntity) -> Inventory:
    if target is Player:
        target.take_damage(10)
    var as_enemy := source as Enemy
    if as_enemy:
        as_enemy.attack()
    var heal_id = Trigger.HEAL
    return Inventory.new()

func dispatch(items: Array[Inventory]) -> void:
    for item in items:
        item.add_item("token")
