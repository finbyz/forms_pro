from functools import reduce
from typing import Any, Generic, TypeVar

import frappe
from frappe.model.document import Document

T = TypeVar("T", bound=Document)


class BaseFactory(Generic[T]):
    factory_traits: list[str]
    doctype: str
    overrides: dict[str, Any]

    @classmethod
    def build(cls, *_factory_traits: str, **overrides: Any) -> T:
        instance = cls(*_factory_traits)
        instance.overrides = overrides
        # Assign doctype last so that it cannot be overridden
        doctype: T = frappe.get_doc(
            {**instance.attributes, **overrides, "doctype": instance.doctype}
        )
        doctype.flags.update(overrides.get("flags", {}))

        return doctype

    @classmethod
    def build_list(
        cls, n: int, *_factory_traits: str, **overrides: Any
    ) -> list[T]:
        return [cls.build(*_factory_traits, **overrides) for _ in range(n)]

    @classmethod
    def create(cls, *_factory_traits: str, **overrides: Any) -> T:
        doctype = cls.build(*_factory_traits, **overrides)
        doctype.insert()
        cls._attach_del(doctype)

        return doctype

    @classmethod
    def create_list(
        cls, n: int, *_factory_traits: str, **overrides: Any
    ) -> list[T]:
        return [cls.create(*_factory_traits, **overrides) for _ in range(n)]

    def __init__(self, *factory_traits: str) -> None:
        self.factory_traits = list(factory_traits)

        valid_traits = [
            name
            for name, value in self.__class__.__dict__.items()
            if isinstance(value, property) and name != "default_attributes"
        ]
        if not set(self.factory_traits).issubset(valid_traits):
            raise TypeError(
                f"traits ({self.factory_traits}) must be a subset of the set of valid traits ({valid_traits})"
            )

    @classmethod
    def _attach_del(cls, obj: Any) -> None:
        """
        Attaches a custom __del__ method to the given object's class.
        """
        TempSubclass = type(
            "TempSubclass",
            (obj.__class__,),
            {"__del__": cls.__del_override__},
        )
        obj.__class__ = TempSubclass

    @property
    def default_attributes(self) -> dict[str, Any]:
        return {}

    @property
    def attributes(self) -> dict[str, Any]:
        return reduce(
            lambda acc, el: {**acc, **getattr(self, el)},
            self.factory_traits,
            self.default_attributes,
        )

    @staticmethod
    def __del_override__(_self: Any) -> None:
        pass
