from textual.widgets import Button

from runconf_ui.state_tree import StateOperation


class EnableDisbableButton(Button):
    def __init__(self, operation: StateOperation, *args, **kwargs):
        '''
        Setup buttons
        '''
        kwargs['label'] = operation.label
        self.operation = operation
        
        super.__init__(*args, **kwargs)
        