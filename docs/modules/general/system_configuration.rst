System Configuration
======================
Runconf-UI uses a YAML file to determine what components are visible to the user. These should be stored in `[your_repo]/runconf-ui-settings/[apparatus].yml`.

There are 3 sections in the configuration file:
1. The "Settings" section. This currently just points to the classes you want made visible in the "main system tree"
2. The "PanelOptions section". This lists the enable/disable panels
3. The "AdjustableAttributes" section. This lists things you want made "adjustable" such as trigger rates


Configuration Overview
-----------------------
The "PanelOptions" section lists the panels that are enabled/disabled. There are 3 kinds of objects
- `components` - These are objects that can be enabled/disabled by OKS directly
- `attributes` - These are attribtues of objects in OKS and require a bit more work to enable/disable. For example, the "TPG" attribute of a "ReadoutApplication" object
- `relationships` - These are relationships between objects in OKS. Which may need to be swapped

We also have an adjustable attributes section which lists items that can set to different values (not just enabled/disabled) at the session level. For example, we can adjust the trigger rate of a given trigger.

The YAML is organised into sub-groups such that the textual will produce tabs for each sub-group. For example:

The configuration should look like this:
.. code-block:: yaml

    Settings:
        # List of classses to show on map panels
        classes_to_show [list str]:

    # PanelOptions are the list of "panels" that display both trees (if view_panel has a name) and lists of what to show
    PanelOptions:
    # Panel ID
        Panel: 

            # Label given to panel
            label [str]:  
            # Display name for attribute map
            view_panel [str]: 

            systems: # List of systems
            - SystemA: # A specific system

                # If we turn off all the subsystems do it also turn of the entire system
                subsytem_dependent [bool]: false 
                # Include a button for enabling/disabling the entire system
                display_full_system [bool]: true 
                
                # List Components are elements that can be enabled/disabled at the session level
                components: 

                    # Component ID. If each_component_seperate is true 
                    # then id needs to be a substring common to all components you want to show
                    - id [str] : 
                    # Component class
                    class [str]: 

                    ~~[[Optional Values]]~~

                    # do these components also live in a seperate subsystem?
                    separate_system [bool]: false 
                    # Subsytem they live in [useful for things like TPC where you want to toggle individual CRPs] 
                    system_label: None  
                    
                    # What if we want lots of components and separate buttons for each one?
                    # Generate a button for each component of class [class] with id containing a substring of ID
                    each_component_separate [bool]: false 

                    # We then filter based on the attributes of these objects
                    filters [List[Dict]]: 
                    # name of the attribute to filter by
                        - attribute [str]: ""
                        # list of values to exclude
                        values List[Any]: []
                    
                    # We can display a tooltip
                    # If the tooltip is an attribute in the object it will display that attribute as the tooltip
                    # For example if an object has a "description" attribute it will display the value of "description
                    tooltip [str]: ""
                
                # We can also toggle the attributes of groups of objects 
                attributes:
                    # Name of the attribute
                    - id [str]:
                    # Segments to search for objects in
                    segment [List[str]]: ["root-segment"]
                    # Class of objects with attribute
                    class [str]: 

                    ~~[[Optional Values]]~~
                    # Attributes may not have simple true/false enabled/disabled states
                    # This lets us over-ride this behaviour and define custom enabled disabled states
                    enabled_state [Any]:
                    disabled_state [Any]:
                    
                    # Subsystem settings (same as component)
                    system_label [str]: 
                    separate_system [bool]: False

                    # Tool tip here will just directly print the string (but only if it's a separate system)
                    tooltip [str]: ""

                # The final thing we can toggle is the relationship between objects
                # As these are essentially attributes most of the interface is the same
                relationships:
                    # Same as attribute:
                    - id [str]:
                    class [str]:
                    segments List[str]: ['root-segment']

                    # Relationship-specific options
                    # We need to know the expected class of object the relationship needs
                    relationship_class [str]:

                    # Name of single/list of config objects that 
                    # object has relationship to when toggled on/off
                    # To remove the relationship entirely just needs to be left as []
                    enabled_state [str | List[str]]: 
                    disabled_state [str | List[str]]: 

        AdjustableAttributes:
            AttributeGroup: # Group of attributes to put in a tab
                - label [str]: # internal label to keep textual sane
                Systems:
                - object_id [str, Optional]: # ID of object containing a given attribute. If left blank it will search for all objects of a given class
                    object_class [str]: # Class of objects with given attribute
                    attribute_name [str]: #Name of attribute to modify 
                    is_hex [bool, optional]: False # Is the attribute stored in hex
                    tooltip [str, optional]: # Attribute to use as the tool tip i.e. "description" when higlighting box

                    # values to filter by
                    filters [List]:
                    - attribute [str]: # attribute to filter by
                        values [List[Any]]: # List of values of that attribute you want to exclude


