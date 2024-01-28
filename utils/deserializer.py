from typing import Type, Any


class Deserializer:
    """A basic Deserializer class for deserializing JSON data into Python class objects.

    Note:
    This Deserializer class is intended to be a simple tool used within the project and is not meant to be used
    as a full-fledged deserializer. It provides a simple deserialization mechanism for basic cases.


    Example:
        Consider the following class and JSON data:
        class Person:
            def __init__(self):
                self.name = ""
                self.age = 0

        json_data = {
            "name": "John",
            "age": 30
        }

        To deserialize the JSON data into a Person object, use the Deserializer as follows:

        person_obj = Deserializer.deserialize(Person, json_data)
        print(person_obj.name)  # Output: "John"
        print(person_obj.age)   # Output: 30
    """

    @staticmethod
    def deserialize(cls: Any, json_data: dict) -> Type:
        """Deserialize JSON data into a Python class object.

        Args:
            cls (Type): The class type to which the JSON data will be deserialized.
            json_data (dict): A dictionary containing the JSON data to be deserialized.

        Returns:
            Type: The class object with attributes updated based on the JSON data.
        """
        if json_data is None:
            return cls

        p_fields = [attr for attr in cls.__dict__ if
                    not callable(getattr(cls, attr)) and not attr.startswith("__")]

        for j_field in json_data:
            if j_field in p_fields:
                cls.__setattr__(j_field, json_data[j_field])

        return cls
