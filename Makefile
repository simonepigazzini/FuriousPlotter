rootsys = /usr

install:
	mkdir -p $(rootsys)/lib/root/fp_plugins
	cp macros/* $(rootsys)/share/root/macros/
	cp draw.py $(rootsys)/bin/
	cp plot_manager.py $(rootsys)/bin/
	cp tree_manager.py $(rootsys)/bin/
	cp fp_utils.py $(rootsys)/lib/root
	cp operations.py $(rootsys)/lib/root
	cp plugins/*py $(rootsys)/lib/root/fp_plugins
	chmod +x $(rootsys)/bin/draw.py

uninstall:
	rm -r $(rootsys)/share/root/macros/CMS_lumi.C
	rm -r $(rootsys)/share/root/macros/setStyle.C
	rm -r $(rootsys)/lib/root/fp_utils.py 
	rm -r $(rootsys)/lib/root/operations.py
	rm -r $(rootsys)/bin/draw.py
	rm -r $(rootsys)/bin/plot_manager.py
	rm -r $(rootsys)/bin/tree_manager.py
	rm -r $(rootsys)/lib/root/fp_plugins

