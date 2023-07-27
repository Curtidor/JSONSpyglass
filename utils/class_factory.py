from typing import List, Any


class ClassFactory:
    """
    A class factory that creates instances of classes based on their names.

    ClassFactory allows you to initialize and store class types by their
    names, and later create new instances of the classes using the stored types.
    """

    _class_types = {}  # Dictionary to store class types with their names

    @staticmethod
    def initialize(class_types: List[type]) -> None:
        """
        Initialize the ClassFactory with a list of class types.

        Args:
            class_types (List[type]): A list of types/classes to be stored in the factory.
        """
        for cls_type in class_types:
            class_name = cls_type.__name__
            ClassFactory._class_types[class_name] = cls_type

    @staticmethod
    def create_instance(class_name: str, *args, **kwargs) -> Any:
        """
        Create a new instance of a class using its name.

        Args:
            class_name (str): The name of the class to create an instance of.
            *args: Additional positional arguments to pass to the class constructor.
            **kwargs: Additional keyword arguments to pass to the class constructor.

        Returns:
            Any: An instance of the specified class.

        Raises:
            ValueError: If the class with the specified name is not found in the factory.
        """
        cls_type = ClassFactory._class_types.get(class_name)
        if cls_type:
            return cls_type(*args, **kwargs)
        else:
            raise ValueError(f"Class '{class_name}' not found in the factory.")
