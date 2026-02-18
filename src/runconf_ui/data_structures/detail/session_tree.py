
from runconf_ui.data_structures.tree_interface import TreeInterface
from conffwk.dal import DalBase
from confmodel_dal import component_disabled

class ConfigTree(TreeInterface[DalBase]):
    '''
    Simple class to turn configuration into a tree, this gives a global state
    '''
    def build_tree(self, top_object: DalBase):
        """Iterative tree building using BFS to avoid recursion overhead"""
        graph = {}
        visited = set()
        queue = [top_object]

        while queue:

            current = queue.pop(0)
            obj_id = id(current)

            if obj_id in visited:
                continue
            visited.add(obj_id)

            rels = self.configuration.relations(current.className(), all=True)
            related_objects_list = []

            for rel in rels:
                related_objects = getattr(current, rel, [])

                if related_objects is None:
                    continue

                if not isinstance(related_objects, list):
                    related_objects = [related_objects]

                related_objects_list.extend(related_objects)

                # Add unvisited objects to queue
                for related in related_objects:
                    if id(related) not in visited:
                        queue.append(related)

            if related_objects_list:
                graph[current] = related_objects_list

        return graph

    def is_disabled(self, obj: DalBase):
        '''
        For resources checks if the resource AND all top level resources are disabled
        other wise just checks if all top level resources are disabled.
        Also checks if all parent objects are disabled.
        '''

        obj_id = id(obj)
        if obj_id in self._is_disabled_cache:
            return self._is_disabled_cache[obj_id]

        # Otherwise we loop through containing resources
        disabled_dals = [self.is_disabled(d) for d in self.configuration.get_dals("Resource") if self.is_nested(d, obj) and d!=obj]

        disabled = all(disabled_dals) and len(disabled_dals)

        if 'Resource' in self.configuration.superclasses(obj.className(), True) and not disabled:
                disabled = component_disabled(obj) or disabled

        # Check if all parent objects are disabled
        if not disabled:
            parents = self.find_parent(obj)
            if parents and all(self.is_disabled(parent) for parent in parents):
                disabled = True

        self._is_disabled_cache[obj_id] = disabled
        return disabled