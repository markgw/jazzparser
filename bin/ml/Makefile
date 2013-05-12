# Builds OCaml executables
SOURCE_DIR = ../../src/ml
COMPILER_OPTS = -I build/

tspath : $(SOURCE_DIR)/tspath.ml
	# Compiling the OCaml source for tspath
	ocamlc $(COMPILER_OPTS) $(SOURCE_DIR)/tspath.ml -o tspath
	# Moving the bytecode files to the build dir
	mv $(SOURCE_DIR)/tspath.cmo $(SOURCE_DIR)/tspath.cmi build/
