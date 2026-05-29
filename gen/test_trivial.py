import os, kisch
OUT=os.path.dirname(os.path.abspath(__file__))+"/_test"
os.makedirs(OUT, exist_ok=True)
p=kisch.Project("test", OUT)
s=p.add_sheet("Test","test_sheet.kicad_sch","Test")
s.root_pos=(50,50)
r=s.place('Device','R','R1','10k',(100,100),footprint='Resistor_SMD:R_0603_1608Metric')
# +3V3 on pin1 (top), GND on pin2 (bottom)
s.power('+3V3', r.pin('1'))
s.power('GND', r.pin('2'))
# PWR_FLAGs coincident with the power-symbol pins to drive the nets
s.power('PWR_FLAG', r.pin('1'))
s.power('PWR_FLAG', r.pin('2'))
p.write_sheet(s)
p.write_root("Trivial test", ["geometry validation"])
p.write_libtables()
# minimal project file
open(OUT+"/test.kicad_pro","w").write('{"meta":{"filename":"test.kicad_pro","version":1},"sheets":[],"libraries":{"pinned_footprint_libs":[],"pinned_symbol_libs":[]}}\n')
print("wrote", OUT)
