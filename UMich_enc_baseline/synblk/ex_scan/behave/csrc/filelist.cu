PIC_LD=ld

ARCHIVE_OBJS=
ARCHIVE_OBJS += _17344_archive_1.so
_17344_archive_1.so : archive.0/_17344_archive_1.a
	@$(AR) -s $<
	@$(PIC_LD) -m elf_i386 -shared  -o .//../testbench.exe.daidir//_17344_archive_1.so --whole-archive $< --no-whole-archive
	@rm -f $@
	@ln -sf .//../testbench.exe.daidir//_17344_archive_1.so $@



VCS_ARC0 =_csrc0.so

VCS_OBJS0 =amcQwB.o 



%.o: %.c
	$(CC_CG) $(CFLAGS) -O -c -o $@ $<


$(VCS_ARC0) : $(VCS_OBJS0)
	$(PIC_LD) -m elf_i386 -shared  -o .//../testbench.exe.daidir//$(VCS_ARC0) $(VCS_OBJS0)
	rm -f $(VCS_ARC0)
	@ln -sf .//../testbench.exe.daidir//$(VCS_ARC0) $(VCS_ARC0)

CU_UDP_OBJS = \


CU_LVL_OBJS = \
SIM_l.o 

CU_OBJS = $(ARCHIVE_OBJS) $(VCS_ARC0) $(CU_UDP_OBJS) $(CU_LVL_OBJS)

