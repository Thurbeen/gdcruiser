extends Node

var player_scene = preload("res://player.tscn")
var config = load("res://config.gd")

func spawn_player() -> Player:
    return player_scene.instantiate()
