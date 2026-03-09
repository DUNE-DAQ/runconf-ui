from rich.tree import Tree
from textual.containers import ScrollableContainer
from textual.widgets import Static, TabbedContent, TabPane
from textual.css.query import NoMatches

class RichTreePanel(ScrollableContainer):
    '''
    Container for the rich tree view of the configuration.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_view = Static("No tree loaded", id="tree_view")
        self.mount(self.tree_view)
    
    def update_tree(self, tree: Tree):
        '''
        Update the tree view with a new rich Tree object.
        '''
        self.tree_view.update(tree)
        
class RichTreeTabbed(TabbedContent):
    '''
    Automatically generates a tabbed interface for multiple rich tree views, one per group.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_panels = {}
    
    def generate_panels(self, tree_dict: dict[str, Tree]):
        '''
        Generate tree panels for each group based on the provided dictionary of rich Tree objects.
        '''
        for group_id, tree_ in tree_dict.items():
            panel = RichTreePanel(id=f"tree_panel_{group_id}")
            panel.update_tree(tree_)
            self.mount(TabPane("MapView", panel, id=group_id))
        
    def update_trees(self, tree_dict: dict[str, Tree]):
        '''
        Update the tree views of existing panels with new rich Tree objects.
        '''
        for group_id, tree_ in tree_dict.items():
            try:
                panel = self.query_one(f"#tree_panel_{group_id}", RichTreePanel)
            # Handle quietly for NoMatches
            except NoMatches:
                continue
            except Exception as e:
                raise e
            if panel:
                panel.update_tree(tree_)