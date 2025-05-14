"This is where the fun begins... I have zero (0) clue about anything web ui"
import nicegui.ui as ui

ui.label('This doesnt quite work like in the tutorial...')

ui.button('click me', color = 'red', on_click = lambda: ui.label('you clicked me!'))

ui.run()

