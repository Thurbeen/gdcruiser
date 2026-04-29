extends Resource

# A pure-data Resource that violates "no autoload from resource" by
# poking at the TurnManager singleton — exactly the case the autoload
# parser is meant to surface.

func apply() -> void:
    TurnManager.advance()
    EventBus.something_happened.emit("healed")
    var note := "TurnManager.advance is not a real call here"  # string-literal: must not trigger.
    # Comment reference: TurnManager.foo  must not trigger either.
    print(note)
