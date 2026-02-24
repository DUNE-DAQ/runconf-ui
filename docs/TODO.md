# TODO:
## YAML Configs
 - Consolidate config formats for disable and adjustables. Right now we have 
    ```
    Systems:
        SystemName:
            components:    {}
            attributes:    {}
            relationships: {}
    ```
    for disable-ables, and
    ```
    Systems:
        {}
    ```
    for adjust-ables. This makes the code unecessarily complex. To combat this,
    the YAML reader classes add a dummy "default" above the system to make
    things have the same format...

- Add more sanity to the YAML format. Rather than the flat format with subclasses we can have
    ```
    Systems:
        - system A: {}
          system B: {}
          SubSystemA:
            subsystemA A: {}
            ...
    ```
