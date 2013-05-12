"""Prototype modules that will later be relocated to elsewhere in the codebase.

The idea of this package is that modules can be created in here that depend 
on the rest of the codebase, but that should not be used from other modules 
(or at least not without the strong proviso that the interfaces may change 
substantially and the modules might disappear altogether).

This makes it easy to prototype new classes and functions without having to 
decide yet where they'll live in the codebase or what their interfaces will 
be. In many cases, a prototyped idea may in fact be dropped altogether. Again, 
this can be done without disturbing the reliability of the rest of the project.

Everything in this package is transient and nothing should live here 
permanently.

"""
