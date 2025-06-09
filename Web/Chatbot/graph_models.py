from neomodel import StructuredNode, StringProperty, IntegerProperty

class PolicyNode(StructuredNode):
    policy_id = StringProperty(unique_index=True)
    name = StringProperty()
    keywords = StringProperty()
    description = StringProperty()
    main_category = StringProperty()
    sub_category = StringProperty()
    region = StringProperty()
    min_age = StringProperty()
    max_age = StringProperty()