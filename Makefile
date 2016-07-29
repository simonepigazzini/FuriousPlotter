rootsys = /usr

install:
	mkdir -p $(rootsys)/etc/root/plugins/FuriousPlotter/
	cp cfg/* $(rootsys)/etc/root/plugins/FuriousPlotter/
	cp macros/* $(rootsys)/share/root/macros/
	cp draw.py $(rootsys)/bin/
	cp operations.py $(rootsys)/lib/root

uninstall:
	rm -r $(rootsys)/etc/root/plugins/FuriousPlotter/
	rm -r $(rootsys)/share/root/macros/CMS_lumi.C
	rm -r $(rootsys)/share/root/macros/setStyle.C
	rm -r $(rootsys)/bin/draw.py
	chmod +x $(rootsys)/bin/draw.py

