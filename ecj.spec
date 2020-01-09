Epoch: 1

%global qualifier R-4.5.2-201602121500
# Taken from MANIFEST.MF
%global bundle_version 3.11.2
%global bundle_qualifier v20160128-0629
%global rhug_timestamp 20131211

%define with_gcjbootstrap %{!?_with_gcjbootstrap:0}%{?_with_gcjbootstrap:1}
%define without_gcjbootstrap %{?_with_gcjbootstrap:0}%{!?_with_gcjbootstrap:1}

Summary: Eclipse Compiler for Java
Name: ecj
Version: 4.5.2
Release: 3%{?dist}
URL: http://www.eclipse.org
License: EPL
Group: Development/Languages
Source0: http://download.eclipse.org/eclipse/downloads/drops4/%{qualifier}/%{name}src-%{version}.jar
Source1: ecj.sh.in
# Use ECJ for GCJ
# cvs -d:pserver:anonymous@sourceware.org:/cvs/rhug \
# export -D %%{rhug_timestamp} eclipse-gcj
# tar cjf ecj-gcj-%%{rhug_timestamp}.tar.bz2 eclipse-gcj
Source2: %{name}-gcj-%{rhug_timestamp}.tar.bz2
# No dependencies are needed for ecj, dependencies are for using of jdt.core which makes no sense outside of eclipse
Source3: https://repo1.maven.org/maven2/org/eclipse/jdt/core/compiler/ecj/%{version}/ecj-%{version}.pom
# Extracted from https://www.eclipse.org/downloads/download.php?file=/eclipse/downloads/drops4/%%{qualifier}/ecj-%%{version}.jar
Source4: MANIFEST.MF

# Always generate debug info when building RPMs (Andrew Haley)
Patch0: %{name}-rpmdebuginfo.patch
Patch1: %{name}-defaultto1.5.patch
# Convert ecj source to be source level 1.5 compatible
# This is necessary when building with gcj
Patch2: ecj-convertto1.5.patch
Patch3: eclipse-gcj-nodummysymbol.patch

BuildRequires: gcc-java >= 4.0.0
BuildRequires: /usr/bin/aot-compile-rpm
BuildRequires: java-gcj-compat

%if ! %{with_gcjbootstrap}
BuildRequires: ant
%endif

Requires: libgcj >= 4.0.0
Requires(post): java-gcj-compat
Requires(postun): java-gcj-compat

Provides: eclipse-ecj = %{epoch}:%{version}-%{release}
Obsoletes: eclipse-ecj < 1:3.4.2-4

%description
ECJ is the Java bytecode compiler of the Eclipse Platform.  It is also known as
the JDT Core batch compiler.

%prep
%setup -q -c
%patch0 -p1
%patch1 -p1
%patch2 -p1

sed -i -e 's|debuglevel=\"lines,source\"|debug=\"yes\"|g' build.xml
sed -i -e "s/Xlint:none/Xlint:none -encoding cp1252/g" build.xml
sed -i -e 's|source=\"1\.6\"|source=\"1\.5\"|g' build.xml
sed -i -e 's|target=\"1\.6\"|target=\"1\.5\"|g' build.xml
sed -i -e 's|import org.eclipse.jdt.core.JavaCore;||g' org/eclipse/jdt/internal/compiler/batch/ClasspathDirectory.java
sed -i -e 's|JavaCore.getOptions()||g' org/eclipse/jdt/internal/compiler/batch/ClasspathDirectory.java
# Insert bundle version into messages.properties
sed -i -e "s|bundle_version|%{bundle_version}|g" org/eclipse/jdt/internal/compiler/batch/messages.properties
sed -i -e "s|bundle_qualifier|%{bundle_qualifier}|g" org/eclipse/jdt/internal/compiler/batch/messages.properties

cp %{SOURCE3} pom.xml
mkdir -p scripts/binary/META-INF/
cp %{SOURCE4} scripts/binary/META-INF/MANIFEST.MF

# Use ECJ for GCJ's bytecode compiler
tar jxf %{SOURCE2}
mv eclipse-gcj/org/eclipse/jdt/internal/compiler/batch/GCCMain.java \
  org/eclipse/jdt/internal/compiler/batch/
%patch3 -p1
cat eclipse-gcj/gcc.properties >> \
  org/eclipse/jdt/internal/compiler/batch/messages.properties
rm -rf eclipse-gcj

# Remove bits of JDT Core we don't want to build
rm -r org/eclipse/jdt/internal/compiler/tool
rm -r org/eclipse/jdt/internal/compiler/apt
rm -f org/eclipse/jdt/core/BuildJarIndex.java
# Depends on Java 6 classes, and is unneeded
rm -f org/eclipse/jdt/internal/compiler/batch/ClasspathJsr199.java

# JDTCompilerAdapter isn't used by the batch compiler
rm -f org/eclipse/jdt/core/JDTCompilerAdapter.java

%build
%if %{with_gcjbootstrap}
  for f in `find -name '*.java' | cut -c 3- | LC_ALL=C sort`; do
    gcj -Wno-deprecated -C $f
  done

  find -name '*.class' -or -name '*.properties' -or -name '*.rsc' -or -name '*.props' |\
    xargs fastjar cf %{name}.jar
%else
   ant -verbose
%endif
gzip ecj.1

%install
mkdir -p $RPM_BUILD_ROOT%{_javadir}
cp -a *.jar $RPM_BUILD_ROOT%{_javadir}/%{name}-%{version}.jar
pushd $RPM_BUILD_ROOT%{_javadir}
ln -s %{name}-%{version}.jar %{name}.jar
ln -s %{name}-%{version}.jar eclipse-%{name}-%{version}.jar
ln -s eclipse-%{name}-%{version}.jar eclipse-%{name}.jar
ln -s %{name}-%{version}.jar jdtcore.jar
popd

# Install the ecj wrapper script
install -p -D -m0755 %{SOURCE1} $RPM_BUILD_ROOT%{_bindir}/ecj
sed --in-place "s:@JAVADIR@:%{_javadir}:" $RPM_BUILD_ROOT%{_bindir}/ecj

# Install manpage
mkdir -p $RPM_BUILD_ROOT%{_mandir}/man1
install -m 644 -p ecj.1.gz $RPM_BUILD_ROOT%{_mandir}/man1/ecj.1.gz

aot-compile-rpm

# poms
install -d -m 755 $RPM_BUILD_ROOT%{_mavenpomdir}
install -pm 644 pom.xml \
    $RPM_BUILD_ROOT%{_mavenpomdir}/JPP-%{name}.pom

%add_to_maven_depmap org.eclipse.jdt core %{version} JPP jdtcore

%post
if [ -x %{_bindir}/rebuild-gcj-db ]
then
  %{_bindir}/rebuild-gcj-db
fi
%update_maven_depmap

%postun
if [ -x %{_bindir}/rebuild-gcj-db ]
then
  %{_bindir}/rebuild-gcj-db
fi
%update_maven_depmap

%files
%defattr(-,root,root,-)
%doc about.html
%{_mavenpomdir}/JPP-%{name}.pom
%{_mavendepmapfragdir}/%{name}
%{_bindir}/%{name}
%{_javadir}/%{name}*.jar
%{_javadir}/eclipse-%{name}*.jar
%{_javadir}/jdtcore.jar
%{_mandir}/man1/ecj*
%{_libdir}/gcj/%{name}

%changelog
* Wed Jun 29 2016 Elliott Baron <ebaron@redhat.com> 1:4.5.2-3
- Update to a newer GCCMain.
- Add a timestamp qualifier to ecj-gcj.tar.bz2.
- Remove eclipse-gcj-compat-4.2.1.patch, no longer necessary. 
- Restore versioned jar.
- Resolves: rhbz#1336481

* Tue Jun 28 2016 Elliott Baron <ebaron@redhat.com> 1:4.5.2-2
- Bump release due to issue with previous build.
- Resolves: rhbz#1336481

* Thu May 19 2016 Elliott Baron <ebaron@redhat.com> 1:4.5.2-1
- Update to upstream 4.5.2 release.
- Add eclipse-gcj-compat-4.2.1.patch and eclipse-gcj-nodummysymbol.patch
  from rhel-7.3 branch.
- Add ecj-convertto1.5.patch.
- Remove ClasspathJsr199.java for 1.5 compatibility.
- Add man page.
- Resolves: rhbz#1336481

* Wed Sep 9 2009 Alexander Kurtakov <akurtako@redhat.com> 1:3.4.2-6
- Add maven pom and depmaps.

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:3.4.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Mar 11 2009 Deepak Bhole <dbhole@redhat.com> 1:3.4.2-4
- Add patch to generate full debuginfo for ecj itself

* Tue Mar 10 2009 Deepak Bhole <dbhole@redhat.com> 1:3.4.2-3
- Add BR for aot-compile-rpm

* Tue Mar 10 2009 Deepak Bhole <dbhole@redhat.com> 1:3.4.2-2
- Add BR for ant

* Fri Mar 6 2009 Andrew Overholt <overholt@redhat.com> 1:3.4.2-1
- 3.4.2

* Tue Dec 9 2008 Andrew Overholt <overholt@redhat.com> 1:3.4.1-1
- 3.4.1
- Don't conditionalize building of gcj AOT bits (we're only building
  this for gcj and IcedTea bootstrapping).

* Mon Jan 22 2007 Andrew Overholt <overholt@redhat.com> 3.2.1-1
- Add eclipse-ecj-gcj.patch.

* Fri Jan 12 2007 Andrew Overholt <overholt@redhat.com> 3.2.1-1
- First version for Fedora 7.
- Add BR: java-devel for jar.

* Thu Nov 02 2006 Andrew Overholt <overholt@redhat.com> 1:3.2.1-1jpp
- First version for JPackage.

* Mon Jul 24 2006 Andrew Overholt <overholt@redhat.com> 1:3.2.0-1
- Add versionless ecj.jar symlink in /usr/share/java.

* Wed Jul 19 2006 Andrew Overholt <overholt@redhat.com> 1:3.2.0-1
- 3.2.0.

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Mon Mar 07 2005 Andrew Overholt <overholt@redhat.com> 1:3.1.0.M4.9
- Don't build for ppc or ia64.

* Sun Feb 20 2005 Andrew Overholt <overholt@redhat.com> 1:3.1.0.M4.6
- Upgrade back to 3.1M4.
- Don't build for i386 and x86_64.
- Provide eclipse-ecj until we can deprecate this package.

* Fri Jan 14 2005 Andrew Overholt <overholt@redhat.com> 3.1.0.M4.4
- build for all but x86

* Thu Jan 13 2005 Andrew Overholt <overholt@redhat.com> 3.1.0.M4.3
- build for ppc exclusively

* Wed Jan 12 2005 Andrew Overholt <overholt@redhat.com> 3.1.0.M4.2
- Add RPM_OPT_FLAGS workaround.

* Tue Jan 11 2005 Andrew Overholt <overholt@redhat.com> 3.1.0.M4.1
- New version.

* Mon Sep 27 2004 Gary Benson <gbenson@redhat.com> 2.1.3-5
- Rebuild with new katana.

* Fri Jul 22 2004 Gary Benson <gbenson@redhat.com> 2.1.3-4
- Build without bootstrap-ant.
- Split out lib-org-eclipse-jdt-internal-compiler.so.

* Tue Jul  6 2004 Gary Benson <gbenson@redhat.com> 2.1.3-3
- Fix ecj-devel's dependencies.

* Wed Jun  9 2004 Gary Benson <gbenson@redhat.com> 2.1.3-2
- Work around an optimiser failure somewhere in ecj or gcj (#125613).

* Fri May 28 2004 Gary Benson <gbenson@redhat.com>
- Build with katana.

* Mon May 24 2004 Gary Benson <gbenson@redhat.com> 2.1.3-1
- Initial Red Hat Linux build.

* Mon May 24 2004 Gary Benson <gbenson@redhat.com>
- Upgraded to latest version.

* Sun Jul 20 2003 Anthony Green <green@redhat.com>
- Add %%doc

* Fri Jul 18 2003 Anthony Green <green@redhat.com>
- Initial RHUG build.
