from runconf_ui.runconf_ui_configuration.object_extractors.multi_adjustable_attribute_extractor import MultiAdjustableAttributeExtractor
from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
from runconf_ui.exceptions import CiderOutOfBoundsException
from textual.widgets import Static, Input, Button
from textual.containers import Grid
from textual.message import Message
import logging

class AdjustableAttributePanel(Static):
    '''
    Panel for adjusting attributes of objects in the system.
    '''
    DELIMITER = "---"
    
    def __init__(self, application_controller: ShifterInterfaceState, opts: dict, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self._application_controller = application_controller
        self._opts = opts

        self._attribute_manager = MultiAdjustableAttributeExtractor(
            application_controller, **opts
        )


    def open_new_session(self):
        self._attribute_manager = MultiAdjustableAttributeExtractor(
            self._application_controller, **self._opts)

    def compose(self):
        # Create an input field for each object
        for object_id, object_value in self._attribute_manager.get_all_states().items():
            
            state = object_value['state']
            attribute = object_value['attribute']
            
            label_name = f"{object_id.replace(' ', '~')}{self.DELIMITER}{attribute.replace(' ', '~')}"
            
            with Grid(id=f"grid-{label_name}", classes="adjustable-attribute-grid"):
                
                yield Static(
                    f"[bold]ID:[/bold] [bold red]{object_id}[/bold red]:\n[bold]Attribute:[/bold] [bold purple]{attribute}[/bold purple]",
                    id=f"label-{label_name}",
                    classes="adjustable-attribute-label adjustable-attribute-name",
                )
            
                yield Input(
                    value=f'{state:3f}',
                    placeholder=f"{state:3f}",
                    id=f"input-{label_name}",
                    classes="adjustable-attribute-input",
                )

                yield Button(
                    "Apply",
                    id=f"apply-{label_name}",
                    classes="adjustable-attribute-button",
                    variant="primary",
                )
                
                yield Button(
                    "Reset",
                    id=f"reset-{label_name}",
                    classes="adjustable-attribute-button",
                    variant="warning",
                )
                
                yield Static(
                    f"[violet]{self._attribute_manager.get_tooltip(object_id, attribute)}",
                    id=f"current-value-{label_name}",
                    classes="adjustable-attribute-current-value adjustable-attribute-label",
                )
    
    
    def on_button_pressed(self, event):
        button_id = event.button.id
    
        base_id_attr = button_id.replace("apply-", "").replace("reset-", "")
        
        ## Now need to split into attribute and object ID
        base_id, attribute = base_id_attr.split(self.DELIMITER)

        logging.info(f"Button pressed: {button_id} for base ID: {base_id} and attribute: {attribute}")
        
        input_id = f"input-{base_id_attr}"
        if "reset" not in button_id and "apply" not in button_id:
            return
        
        if "reset" in button_id:
            self._attribute_manager.reset_value(base_id, attribute)
            input: Input = self.query_one(f"#{input_id}")
            input.clear()
        
        elif "apply" in button_id:
            input_value = self.query_one(f"#{input_id}").value
            
            try:
                self._attribute_manager.set_state(base_id, attribute, input_value)
            except Exception as e:
                
                message = f"Error setting attribute {attribute} for object {base_id}. Value: {input_value} is out of bounds or invalid."
                self.post_message(self.AttributeOutOfBounds(base_id, message))
                return


        self.query_one(f"#current-value-{base_id_attr}").update(
            self._attribute_manager.get_tooltip(base_id, attribute)
        )
        
        self._application_controller.current_state.update({self.id: self.get_current_states()})
        
    def get_current_states(self) -> dict:
        """
        Returns the current states of all adjustable attributes in the panel.
        :return: A dictionary mapping object IDs to their current attribute states.
        """
        return self._attribute_manager.get_all_states()

    class AttributeOutOfBounds(Message):
        """
        Message to indicate that an attribute value is out of bounds.
        """
        def __init__(self, object_id: str, message: str):
            super().__init__()
            self.object_id = object_id
            self.message = message
