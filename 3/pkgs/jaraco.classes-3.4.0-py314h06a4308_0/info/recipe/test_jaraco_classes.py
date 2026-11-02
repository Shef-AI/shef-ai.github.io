import pytest
from jaraco.classes import ancestry, meta, properties

# -----------------------
# ancestry.py
# -----------------------

def test_iter_subclasses_finds_direct_and_indirect():
    class A: ...
    class B(A): ...
    class C(B): ...

    subs = list(ancestry.iter_subclasses(A))
    # Should find both direct and indirect subclasses
    assert B in subs
    assert C in subs
    # Order should be depth-first and without duplicates
    assert len(subs) == len(set(subs))


def test_all_classes_returns_mro():
    class X: ...
    class Y(X): ...
    class Z(Y): ...

    classes = list(ancestry.all_classes(X))
    # Unique
    assert len(classes) == len(set(classes))
    # For X, MRO contains X and object (no descendants)
    assert X in classes
    assert object in classes
    assert Y not in classes
    assert Z not in classes


# -----------------------
# meta.py
# -----------------------

def test_leaf_classes_meta_tracks_only_leaves():
    class Parent(metaclass=meta.LeafClassesMeta):
        pass

    # At definition time, Parent is the only "leaf"
    assert Parent in Parent._leaf_classes
    assert len(Parent._leaf_classes) == 1

    class Child(Parent):
        pass

    # After adding Child, leaves should be only Child
    assert Child in Parent._leaf_classes
    assert Parent not in Parent._leaf_classes

    class Sibling(Parent):
        pass

    # Now leaves should be Child and Sibling
    assert {Child, Sibling} == Parent._leaf_classes


def test_tag_registered_builds_registry_by_attr():
    class Base(metaclass=meta.TagRegistered):
        # The base class itself is not usually added to the registry
        pass

    class Alpha(Base):
        tag = "alpha"

    class Beta(Base):
        tag = "beta"

    # Both classes should share the same registry
    assert hasattr(Base, "_registry")
    assert Base._registry is Alpha._registry is Beta._registry

    assert Base._registry["alpha"] is Alpha
    assert Base._registry["beta"] is Beta

    # Ensure the attribute name is taken from attr_name
    assert getattr(meta.TagRegistered, "attr_name") == "tag"


# -----------------------
# properties.py
# -----------------------

def test_non_data_property_behaves_on_instance_and_class():
    class X:
        @properties.NonDataProperty
        def foo(self) -> int:
            return 4

    x = X()
    # On the instance — computed value
    assert x.foo == 4
    # On the class — descriptor (non-data descriptor)
    assert isinstance(X.foo, properties.NonDataProperty)

    # A non-data descriptor does not prevent setting an attribute
    # with the same name in the instance __dict__
    x.__dict__['foo'] = 10
    assert x.foo == 10  # instance attribute overrides the descriptor


def test_classproperty_exposes_class_level_value():
    class C:
        _val = 3

        @properties.classproperty
        def val(cls) -> int:  # noqa: N805 (cls is conventional)
            return cls._val

    # Accessible as a "class property"
    assert C.val == 3
    # Accessible through an instance — same value
    assert C().val == 3

    # Changing the class attribute updates the property
    C._val = 7
    assert C.val == 7
    assert C().val == 7


def test_classproperty_assignment_rules():
    """
    classproperty is a data descriptor:
    - Assigning on the instance is forbidden (triggers __set__ -> AttributeError).
    - Assigning on the class overwrites the attribute in C.__dict__ (allowed).
    """
    class C:
        _val = 1

        @properties.classproperty
        def val(cls) -> int:
            return cls._val

    # Baseline
    assert C.val == 1
    inst = C()
    assert inst.val == 1

    # Instance assignment is forbidden
    with pytest.raises(AttributeError):
        setattr(inst, "val", 7)
    assert inst.val == 1
    assert C.val == 1

    # Class assignment overwrites the descriptor (allowed)
    setattr(C, "val", 5)
    assert C.val == 5
    assert inst.val == 5