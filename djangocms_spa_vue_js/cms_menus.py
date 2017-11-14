from cms.models import Page
from django.utils.text import slugify
from menus.base import Modifier
from menus.menu_pool import menu_pool

from djangocms_spa_vue_js.menu_helpers import get_node_route


class VueJsMenuModifier(Modifier):
    """
    This menu modifier extends the nodes with data that is needed by the Vue JS route object and by the frontend to
    render all contents. Make sure all your custom models are attached to the CMS menu.

    Expected menu structure:
    - Home
        - Page A
        - Page B
            - Page B1
        - Page C
        - News list (App hook)
            - News detail A
            - News detail B
    """
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        # If the menu is not yet cut, don't do anything.
        if post_cut:
            return nodes

        # Prevent parsing all this again when rendering the menu in a second step.
        if hasattr(self.renderer, 'vue_js_structure_started'):
            # return nodes
            pass  # REPORT ISSUE: this does not work as expected - even though vue_js_structure_started is set to True, nodes do not contain route related attr
        else:
            self.renderer.vue_js_structure_started = True

        router_nodes = []
        named_route_path_patterns = {}

        for node in nodes:
            if node.attr.get('login_required') and not request.user.is_authenticated:
                continue

            if node.attr.get('is_page'):
                node.attr['cms_page'] = Page.objects.get(id=node.id)

            node_route = get_node_route(request=request, node=node, renderer=self.renderer)

            if node.attr.get('is_page'):
                # for page type nodes add all title translations on top level
                title = node.attr['cms_page'].title_set.get(language=request.LANGUAGE_CODE)
                node_route['title'] = title.page_title if title.page_title else title.title

            named_route_path_pattern = node.attr.get('named_route_path_pattern')
            if named_route_path_pattern:
                named_route_path = node.attr.get('named_route_path')
                if named_route_path:
                    path = named_route_path
                else:
                    # Override the path with the pattern (e.g. 'parent/foo' to 'parent/:my_path_pattern')
                    path = '{parent_url}{path_pattern}/'.format(parent_url=node.parent.get_absolute_url(),
                                                                path_pattern=named_route_path_pattern)
                node_route['path'] = path
                node_route['name'] = slugify(path)  # Use the same name for all nodes of this route.

                if named_route_path_pattern not in named_route_path_patterns.keys():
                    # Store the index of this route in a dict of patterns. We need this to be able to override the
                    # named route with the selected node (see the next condition).
                    named_route_path_patterns[named_route_path_pattern] = len(router_nodes)
                elif node.selected:
                    # Update the router config with the fetched data of the selected node.
                    index_of_first_named_route = named_route_path_patterns[named_route_path_pattern]
                    node.attr['vue_js_route'] = node_route
                    router_nodes[index_of_first_named_route] = node
                    continue  # Skip this iteration, we don't need to add a named route twice.
                else:
                    continue  # Ignore named routes for path patterns that have already been processed.

            node.attr['vue_js_route'] = node_route
            router_nodes.append(node)

        return router_nodes

menu_pool.register_modifier(VueJsMenuModifier)
