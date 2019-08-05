#This script is designed to run with Understand as an Interactive Report
# Version Info
#
# 1.0 First Versioned Release 2016-12-20
# 1.1 Fix minor bug on Windows where it wouldn't open the graph if there was a space in the path
# 1.2 Add 4 additional metric threshholds, fix issue with nested directories in Architect view  2016-12-29
# 1.3 Add Metrics csv, remove standard system classes from calcuations
# 1.4 Add separate class metric export, only generate metrics on real classes defined in project, all line counts are based on loc, not raw lines
# 1.5 Add LOC for class metrics export, show # of classes
# 1.6 Add architecture type to class metric export
# 1.7 Change some of the default values
# 1.8 Fix bug with Borderline Core-Periphery if there was only one cyclic group. Also add Central Size metric.
# 1.9 For empty file aggregate metrics export zero instead of blank
# 1.10 Fix Central Size metric pointing to core, add core and central for all projects
# 1.11 Add new metric, Useful Comment to Code Ratio
# 1.12 Add new metric, Useful Lines of Code, restructure report to show overly complex files.
# 1.13 Fix bug with overly complex metrics, hide core size and complexity unless the Architecture is Core-Periphery
# 1.14 Fix bug with missing class declarations
# 1.15 Add Treemap graph. Requires Understand build 930
# 1.16 Update metrics to include languages without classes
# 1.17 Add duplicate code metrics
# 1.18 Ignore includes and imports when counting duplicate code
# 1.19 Fix div by zero error if the project has 0 useful lines of code
# 1.20 Round percentages
# 1.21 Fix random "tree" error
# 1.22 Handle Javascript Class-Functions correctly
# 1.23 Add more decimal values to propagation cost
our $version = "1.23";

use strict;
use Data::Dumper;
use List::Util qw( min max sum);
use File::Basename;
use Getopt::Long;
use Understand;

#************************** Globals *****************************
our $funcKindString = "ada entry, ada function, ada package, ada procedure, ada protected, ada task,"
  ."c function,"
  ."cobol program,"
  ."csharp method,"
  ."fortran block data, fortran function, fortran interface, fortran program, fortran subroutine,"
  ."java method,"
  ."jovial file, jovial subroutine,"
  ."pascal compunit, pascal function, pascal procedure,"
  ."vhdl procedure, vhdl function, vhdl process, vhdl architecture,"
  ."web function";
  
our $abort_called;
our @visibilityMatrix;
our @stack;
our $index;
our $analyzedCount; #How many files have been analyzed;
our %fileObjsByEntID; #hash of the same file objects by entityid
our $fileCount;
our $percentComplete;
our $currentLexeme;  
our $commentStartLine; #Track the current comment start
our %lexers = ();
our @matches;  #array to track duplicate lines
our %codeHashes; #Hash for tracking all code locations for building duplicate list
our $minDupLines; #Minimum # lines to match for duplicates
our $minDupChars=20; #Minimum # characters to match for duplicates
my $dbPath;
my $help;
my %options;


#************************* Main *********************************
my $report = convertIreport->new();
init($report);
setupOptions();
generate($report);


sub generate {
  my $report = shift;
  
  $abort_called=0;
  @visibilityMatrix=();
  @stack=();
  $index=0;
  $analyzedCount=0; #How many files have been analyzed;
  %fileObjsByEntID=(); #hash of the file objects by entityid
  $fileCount=0;
  $percentComplete=0;
  my $start_run = time();
  $percentComplete=0;
  $analyzedCount=0;
  @matches = ();
  %lexers = ();
  %codeHashes = ();
  my $outputDir = $report->option->lookup("outputDir");
  my $createTestFiles = $report->option->lookup("createTestFiles");
  my $createMetricsFiles = $report->option->lookup("createMetrics");
  my $createArch = $report->option->lookup("createArch");
  my $maxFileSize = $report->option->lookup("MaxFileSize");
  my $maxCBOThreshold = $report->option->lookup("MaxCBOThreshold");
  my $maxWMC=$report->option->lookup("MaxWMC");
  my $maxWMCM=$report->option->lookup("MaxWMCM");
  my $maxRFC=$report->option->lookup("MaxRFC");
  $minDupLines = $report->option->lookup("DuplicateMinLines");
  $minDupChars = $report->option->lookup("DuplicateMinChars");
  
  
  my $outputFileName;
  my $largeFileCount = 0;
  my $slash = "/";
  $slash = "\\" if $^O eq 'MSWin32';
  my %directoryList;
  my @fileLines;
  
  
  #Check file locations
  if (! $outputDir){
    die usage("Specify Output Directory in options to save files\n");
  }elsif($outputDir){
    my $success = mkdir("$outputDir");
    if (!$success && ! -e $outputDir){
      die usage("Could not create $outputDir, $!\n");
    }
  }
  
  #Get the project name and path
  add_progress($report,.005,"Initializing");
  #$report->progress(1,"Initializing");
  $report->db->name() =~ /(.*[\/\\])([^\/\\]*)\.udb/;
  my $projectName = ucfirst($2);
  

  # Initialize the initial data structures
  my @fileObjList; # List of file objects sorted alphabetically by directory name
  my @titlesList; #An array of file names in alpha order for printing the DSM and visibility Matrix

  my $count=0;
  my $projUsefulCommentCount = 0;
  my $projUsefulLineCount = 0;
  my $overlyComplexFile = 0;
  my $overlyComplexCoreFile = 0;
  my $overlyComplexCentralFile = 0;
  add_progress($report,.015,"Analyzing dependencies");
  my @fileEnts = sort {dirname($a->relname) cmp dirname($b->relname)|| $a->relname cmp $b->relname} $report->db->ents("file ~unknown ~unresolved");
  foreach my $fileEnt (@fileEnts){
    add_progress($report,.02*10/scalar @fileEnts,"Analyzing dependencies") unless $count % 10;
    Understand::Gui::yield();
    next if $fileEnt->library();
    return if $abort_called;
    my $loc = $fileEnt->metric("CountLineCode");
    
    my $usefulComments = 0;
    my $uselessLines = 0;
    my $lexer = $fileEnt->lexer(0, 8, 1, 0);
    if ($lexer){
      $lexers{$fileEnt->id}=$lexer;
      $usefulComments = usefulCommentCount($fileEnt, $lexer);
      $uselessLines = uselessLineCount($fileEnt, $lexer);
      makeDuplicateCodeHash($fileEnt, $lexer);
    }
    
    
    my $uloc = $loc - $uselessLines;
    $projUsefulCommentCount += $usefulComments;
    $projUsefulLineCount += $uloc;
    push @fileLines,$loc;
    my $fileObj = new fileObj($count,$fileEnt);
    if ($uloc >$maxFileSize){
      $largeFileCount++;
    }
    $fileObjList[$count] = $fileObj;
    $titlesList[$count] = $fileObj->{relname};
    $fileObj->{loc} = $loc;
    $fileObj->{uloc} = $uloc;
    $fileObj->{usefulCommentToCode} = 0;
    $fileObj->{usefulCommentToCode} = sprintf("%.1f",$usefulComments/$loc) if $loc;
    $fileObj->{commentToCode} = $fileEnt->metric("RatioCommentToCode");
    $fileObjsByEntID{$fileObj->{entid}}= $fileObj;  #Create a hash to easily lookup the order of each file
    my $depends = $fileEnt->depends;
    if ($depends){
      foreach my $depEnt ($depends->keys()){
        if ($depends->value($depEnt)){
          push @{$fileObj->{depends}},$depEnt->id;
        }
      }
    }
    #add directory information
    my $directory = dirname($fileEnt->relname());
    $directory =~ s'\\'\\\\'g;
    $directoryList{$directory}{"first"}=$count unless $directoryList{$directory}{"size"};
    $directoryList{$directory}{"size"}++;
    $count++;
  }
  $fileCount = scalar @fileObjList; #Number of files in the project
  
  #identify duplicate code
   foreach(values %codeHashes){
     push @matches, $_ if $_->getLocCount > 1;
   }
    removeDuplicates();
    fillMatchValues();
    removeDuplicates();
  
  if ($createMetricsFiles){
    my $dupFile = $outputDir.$slash."duplicates.txt";
    open (FILE,'>',$dupFile) || die ("Couldn't open $dupFile $!\n");
  }
   my $duplicateLOC = 0;
   my $matchOutputString;
  foreach my $match (@matches){
    $match->updateFileMetrics();
    $duplicateLOC +=($match->getNumLines * $match->getLocCount);
	$matchOutputString .= $match->printMatch();
  }
  print FILE $matchOutputString if $createMetricsFiles;
  close FILE if $createMetricsFiles;
  
  #Populate Design Structure Matrix for each file based off of Understand dependencies
  my @designStructureMatrix; #Array holding the DSM
  foreach my $fileObj (@fileObjList){
    foreach my $depID (@{$fileObj->{depends}}){
        $designStructureMatrix[$fileObj->{id}][$fileObjsByEntID{$depID}->{id}]= 1;
    }             
  }
  if($createTestFiles){
    #Print the Design Structure matrix to an output file
    add_progress($report,.02,"Saving DSM to output file");
    Understand::Gui::yield();
    return if $abort_called;
    $outputFileName = $outputDir."\\1. $projectName Initial Design Structure Matrix.txt";
    printSquareMatrix(\@titlesList ,\@designStructureMatrix,$outputFileName);
  }

  # Calculate the  Transitive Closure via depth first traversal, also the Visibility Fan ins and outs
  printprogress($report,.10,"Calculating Transitive Closure");
  for (my $k = 0; $k < $fileCount; $k++){
    strongconnect($report,$fileObjList[$k]) unless $fileObjList[$k]->{index};
    
  }
    for (my $i = 0; $i < $fileCount; $i++){
      for (my $j = 0; $j < $fileCount; $j++){
        $fileObjList[$j]->vfiInc if $visibilityMatrix[$i][$j];
        $fileObjList[$i]->vfoInc if $visibilityMatrix[$i][$j];
    }
  }

  if($createTestFiles){
    #Print the Transitive Structure matrix to an output file
    add_progress($report,.02,"Print the Transitive Structure matrix to an output file");
    Understand::Gui::yield();
    return if $abort_called;
    $outputFileName = $outputDir."\\2. $projectName Visibility Matrix.txt";
    printSquareMatrix(\@titlesList ,\@visibilityMatrix,$outputFileName);
   
  }

  printprogress($report,.85,"Identifying Cyclic Groups");

  #Identify the cyclic groups of the system and identify the largest.
  my %cyclicGroups; #The cyclic group id for each file
  my @sorted = sort {$b->{vfi} <=> $a->{vfi} || $a->{vfo} <=> $b->{vfo} } @fileObjList;
  my @m;
  my $prev;
  my $curGroup=1; 
  my $counter =0;
  foreach my $file (@sorted){
    if (! $prev  || $file->{vfi} == 1 || $file->{vfo} == 1 
          || $file->{vfi} != $prev->{vfi} || $file->{vfo} != $prev->{vfo}){
        $m[$counter]=1;
    }
    elsif ($file->{vfi} > 1 && $file->{vfo} >1 
         && $file->{vfi} == $prev->{vfi} && $file->{vfo} == $prev->{vfo}){
      $m[$counter]=$m[$counter-1]+1;
    }
    
    #This item consitutes the begining of a new cyclic group, label the previous group
    if ($m[$counter]<$m[$counter-1]){
      my $sizeN = min ($m[$counter-1],$prev->{vfi},$prev->{vfo});
      for( my $i=$m[$counter-1];$i>=1;$i--){
        $sorted[$counter-$i]->{group} = $curGroup
      }
      $cyclicGroups{$curGroup}{size}=$sizeN;
      $cyclicGroups{$curGroup}{vfi}= $prev->{vfi};
      $cyclicGroups{$curGroup}{vfo}= $prev->{vfo};
      $curGroup++;
    }
    
    $prev = $file;
    $counter++;
  }

  if($createTestFiles){   
    $outputFileName = $outputDir."\\3. $projectName Visibility Fan In and Out.txt";
    my $length = length longestItem(@titlesList);
    open (FILE,'>',"$outputFileName") || die ("Couldn't open $outputFileName $!\n");
      print FILE sprintf("%${length}s VFI VFO  Group   Size\n",'');
      foreach my $file (sort{$b->{vfi} <=> $a->{vfi} || $a->{vfo} <=> $b->{vfo} ;}@fileObjList){
        my $group =$file->{group};
        my $groupSize;
        $groupSize = $cyclicGroups{$group}{size} if $group;
        print FILE sprintf("%${length}s  %d   %d     %s      %s\n", $file->{relname},$file->{vfi},$file->{vfo},$group,$groupSize);
      }
      close FILE;
  }

  #Determine the Architecture type of the project
  my $projectArchitectType = "Hierarchical"; #default
  my $coreGroup;
  my $largestGroupID;
  if (%cyclicGroups){
    #Find the largest and second largest Groups
    my @orderedGroupIDs = sort {$cyclicGroups{$b}{size} <=> $cyclicGroups{$a}{size}}  keys %cyclicGroups;
    $largestGroupID = $orderedGroupIDs[0] if @orderedGroupIDs;
    my $secondLargestID= $orderedGroupIDs[1] if scalar @orderedGroupIDs > 1;
    
    if ($cyclicGroups{$largestGroupID}{size} >= $fileCount *.04){
      $projectArchitectType = "Multi-Core";
      if (! $secondLargestID || $cyclicGroups{$largestGroupID}{size} >= $cyclicGroups{$secondLargestID}{size} * 1.5){
        $projectArchitectType = "Borderline Core-Periphery";
        $coreGroup = $largestGroupID;
      }
    }
    if ($cyclicGroups{$largestGroupID}{size} >= $fileCount *.06){
      $projectArchitectType = "Core-Periphery";
      $coreGroup = $largestGroupID;
    }
  }

  #Median Partition Component Types
  #First calculate the median VFI and VFO
  my @vfoList;
  my @vfiList;
  foreach my $file (@fileObjList){
    push @vfoList,$file->{vfo};
    push @vfiList,$file->{vfi};
  }
  my $VFIm = median(@vfiList);
  my $VFOm = median(@vfoList);
  my %mGroupSize;
  foreach my $file (@fileObjList){
    if($file->{vfi} == 1 && $file->{vfo} ==1){
      $file->{componentM} = "Isolate";
      $mGroupSize{Isolate}++;
    }elsif ($file->{vfi}>= $VFIm && $file->{vfo}< $VFOm){
      $file->{componentM} = "Shared";
      $mGroupSize{Shared}++;
    }elsif ($file->{vfi}>= $VFIm && $file->{vfo}>= $VFOm){
        $file->{componentM} = "Core";
        $mGroupSize{Core}++;
    }elsif ($file->{vfi}< $VFIm && $file->{vfo} < $VFOm){
        $file->{componentM} = "Peripheral";
        $mGroupSize{Peripheral}++;
    }elsif($file->{vfi}< $VFIm && $file->{vfo} >= $VFOm){
        $file->{componentM} = "Control";
        $mGroupSize{Control}++;
    }
  }

  #Create a new DSM based off the Median View
  my @medianOrderedObjectList = sort sortByMedian @fileObjList;
  my @medianDSM;
  my @medianTitles;
  $count=0;
  my %medianOrderedObjectByEntID;
  foreach my $file (@medianOrderedObjectList){
    $medianOrderedObjectByEntID{$file->{entid}}=$count;
    $file->{medianOrder}=$count;
    $medianTitles[$count] = $file->{relname}." [".$file->{componentM}."]";
    $count++;
  }
  $count=0;
  foreach my $file (@medianOrderedObjectList){
    foreach my $dep (@{$file->{depends}}){
      return if $abort_called;
      Understand::Gui::yield();
      $medianDSM[$count][$medianOrderedObjectByEntID{$dep}]= 1;
    }
    $count++;    
  }
  $count=0;

  if($createTestFiles){
    #Print the Median matrix to an output file
    add_progress($report,.02,"Print the Median matrix to an output file");
    return if $abort_called;
    Understand::Gui::yield();
    $outputFileName = $outputDir."\\4. $projectName Median Matrix.txt";
    printSquareMatrix(\@medianTitles ,\@medianDSM,$outputFileName);
  }

  
  #determine if the project has a Core-Periphery Group
  
  my %cpGroupSize;
  if ( $coreGroup){
    add_progress($report,.04,"Analyzing Core-Periphery Group");
    return if $abort_called;
    Understand::Gui::yield();
    #Core-Periphery Partition
    my $VFIc = $cyclicGroups{$coreGroup}{vfi};
    my $VFOc = $cyclicGroups{$coreGroup}{vfo};
    foreach my $file (@fileObjList){
      if($file->{vfi} == 1 && $file->{vfo} ==1){
        $file->{componentCP} = "Isolate";
        $cpGroupSize{Isolate}++;
      }elsif ($file->{group} == $coreGroup){
        $file->{componentCP} = "Core";
        $cpGroupSize{Core}++;
      }elsif ($file->{vfi}>= $VFIc && $file->{vfo}< $VFOc){
          $file->{componentCP} = "Shared";
          $cpGroupSize{Shared}++;
      }elsif ($file->{vfi}< $VFIc && $file->{vfo} < $VFOc){
          $file->{componentCP} = "Peripheral";
          $cpGroupSize{Peripheral}++;
      }elsif($file->{vfi}< $VFIc && $file->{vfo} >= $VFOc){
          $file->{componentCP} = "Control";
          $cpGroupSize{Control}++;
      }
    }
    
    
    
    #Create a new DSM based off the Core-Periphery View
    my @coreOrderedObjectList = sort sortByCorePeriphery @fileObjList;
    my @corePeripheryDSM;
    my @coreTitles;
    $count=0;
    my %coreOrderedObjectsByEntID;
    foreach my $file (@coreOrderedObjectList){
      $file->{coreOrder}=$count;
      $coreOrderedObjectsByEntID{$file->{entid}}=$count;
      $coreTitles[$count] = $file->{relname}." [".$file->{componentCP}."]";
      $count++;
    }
    $count=0;
    foreach my $file (@coreOrderedObjectList){
      foreach my $dep (@{$file->{depends}}){
        $corePeripheryDSM[$count][$coreOrderedObjectsByEntID{$dep}]= 1;
      }
      $count++;    
    }
    if($createTestFiles){
    #Print the Core-Periphery matrix to an output file
      add_progress($report,.02,"Print the Core-Periphery matrix to an output file");
      return if $abort_called;
      Understand::Gui::yield();
      $outputFileName = $outputDir."\\5. $projectName Core-Periphery Matrix.txt";
      printSquareMatrix(\@coreTitles ,\@corePeripheryDSM,$outputFileName);
    }
  }
  
  #Calculate Metrics
  printprogress($report,.95,"Calculating Metrics");

  #class Metric calculation
  my @cbos;
  my $cbosOver;
  my @wmcs;
  my $wmcsOver;
  my @wcmcyclos;
  my $wmccyclosOver;
  my @rfcs;
  my $rfcsOver;
  my $classCount;
  my @classes = $report->db->ents("class ~unknown ~unresolved ~unnamed");
  if (@classes){
    if ($createMetricsFiles){
      my $csvFile = $outputDir.$slash."classMetrics.csv";
      open (FILE,'>',$csvFile) || die ("Couldn't open $csvFile $!\n");
      print FILE "Class, Kind, Filename, CBO, WMC, WMC-McCabe, RFC, LOC, Median Group, CP Group\n";
    }
     
    #Loop through each class to generate the class metrics
    foreach my $class (sort{lc($a->longname()) cmp lc($b->longname());} @classes){
      next if $class->library();
      my $declRef = getDeclRef($class);
      next unless $declRef;
      my $declFile = $declRef->file;
      next unless $declFile;
      my $filename = $declFile->longname(1);
      my $fileObj = $fileObjsByEntID{$declFile->id()};
      my $cbo =$class->metric("CountClassCoupled");
      my $wmc =$class->metric("CountDeclMethod");
      my $wmcm = $class->metric("SumCyclomatic");
      my $rfc = $class->metric("CountDeclMethodAll")+getCalledMethodCount($class);
      my $loc = $class->metric("CountLineCode");
      push (@cbos,scalar($cbo));
      push (@wmcs,scalar($wmc));
      push (@wcmcyclos,scalar($wmcm));
      push (@rfcs,scalar($rfc));
      $classCount++;
      if($createMetricsFiles){ # If generating the metrics file associate the max class metric with the file
        print FILE '"'.$class->longname."\",\"".$class->kindname."\",\"$filename\",$cbo,$wmc,$wmcm,$rfc,$loc,".$fileObj->{componentM}.",".$fileObj->{componentCP}."\n";
          $fileObj->{maxCBO} = $fileObj->{maxCBO} < $cbo ? $cbo : $fileObj->{maxCBO};
          $fileObj->{maxWMC} = $fileObj->{maxWMC} < $wmc ? $wmc : $fileObj->{maxWMC};
          $fileObj->{maxWMCM} =$fileObj->{maxWMCM} < $wmcm ? $wmcm : $fileObj->{maxWMCM};
          $fileObj->{maxRFC} = $fileObj->{maxRFC} < $rfc ? $rfc : $fileObj->{maxRFC};
      }
    }
    close(FILE) if $createMetricsFiles;
  }
  my $csvString = "Filename, LOC, UsefulLOC, DuplicateUsefulLOC, CommentToCodeRatio, UsefulCommentToCodeRatio, MaxCBO, MaxWMC, MaxWMC-McCabe, MaxRFC, Median Group, CP Group,Threshold Violations\n";
    foreach my $file (@fileObjList){
      my $violations = 0;
      $violations ++ if $file->{maxCBO} > $maxCBOThreshold;
      $violations ++ if $file->{maxWMC} > $maxWMC;
      $violations ++ if $file->{maxWMCM} > $maxWMCM;
      $violations ++ if $file->{maxRFC}  > $maxRFC;
      $violations ++ if $file->{uloc} > $maxFileSize;
      $file->{violations} = $violations;
      if ($violations > 3){
        $overlyComplexFile++;
        if ($file->{componentM} eq 'Core' ){
          $overlyComplexCentralFile++;
        }
        if ($file->{componentCP} eq 'Core'){
          $overlyComplexCoreFile++;
        }
      }
    #Export the per file metrics
    if($createMetricsFiles){

      $csvString .= '"'.$file->{longname}.'",';
      $csvString .= $file->{loc}.",";
      $csvString .= $file->{uloc}.",";
      $csvString .= $file->{duplicateLOC}.",";
      $csvString .= $file->{commentToCode}.",";
      $csvString .= $file->{usefulCommentToCode}.",";
      $csvString .= ($file->{maxCBO}?$file->{maxCBO}:"0") .",";
      $csvString .= ($file->{maxWMC}?$file->{maxWMC}:"0").",";
      $csvString .= ($file->{maxWMCM}?$file->{maxWMCM}:"0").",";
      $csvString .= ($file->{maxRFC}?$file->{maxRFC}:"0").",";
      $csvString .= $file->{componentM}.",";
      $csvString .= $file->{componentCP}.",";
      $csvString .= $violations."\n";
    }
    
  }
  if ($createMetricsFiles){
    my $csvFile = $outputDir.$slash."fileMetrics.csv";
    open (FILE,'>',$csvFile) || die ("Couldn't open $csvFile $!\n");
    print FILE  $csvString ;
    close FILE;
  }
  
  # Create The Treemap 
  my $treemapString;
  my %treeMapFileNames;
  foreach my $file (@fileObjList){

    my $name = $file->{name};
    $treeMapFileNames{$name}++;
    if ($treeMapFileNames{$name} > 1){
      $name.="(".$treeMapFileNames{$name}.")";
    }
    my $relname = $file->{relname};
    $relname =~ s/\\/\\\\/g;
    
    $treemapString .= "['$name','";
    if ($coreGroup){
      $treemapString .= $file->{componentCP};
    }else{
      $treemapString .= $file->{componentM};
    }
    $treemapString .= "',".$file->{uloc}.",".$file->{violations}.",'$relname'],\n";
  }

  my $treemapFile = $outputDir.$slash."treemap.html";
  my $output = treemapHTML();
  $output =~ s/<<TREEMAPDATA>>/$treemapString/;
  open (FILE,'>',$treemapFile) || die ("Couldn't open $treemapFile $!\n");
  print FILE  $output ;
  close FILE;
  
  
  print "DEBUG: sumVFO: ".(sum @vfoList)."\n";
  print "DEBUG: fileCount: $fileCount\n";
  print "DEBUG: equation: ".(sum @vfoList)." * 100 / $fileCount^2 \n";
  print "DEBUG: Answer: ".((sum @vfoList) *100/($fileCount * $fileCount))."\n";
  
  my @metrics;
  my @metricNames;
  push @metrics,$projectName;
  push @metricNames,"Project Name";
  push @metrics, sprintf("%.3f",((sum @vfoList) *100/($fileCount * $fileCount))) if $fileCount;
  push @metricNames,"Propagation Cost" if $fileCount;;
  push @metrics,$projectArchitectType;
  push @metricNames,"Architecture Type";
  if ($fileCount){
    if ($coreGroup){
      push @metrics, sprintf("%.1f%",($cyclicGroups{$largestGroupID}{size}*100/$fileCount));
      push @metricNames,"Core Size";
    }
    push @metrics, sprintf("%.1f%",($mGroupSize{Core}*100/$fileCount));
    push @metricNames,"Central Size";
  }
  
  push @metrics, $report->db->metric("CountLineCode");
  push @metricNames,"Software Lines of Code (SLOC)";
  push @metrics, $projUsefulLineCount;
  push @metricNames,"Useful Lines of Code (ULOC)";
  push @metrics, $duplicateLOC;
  push @metricNames,"Duplicate Useful Lines of Code";
  if ($projUsefulLineCount){
    push @metrics, (sprintf("%.1f%",$projUsefulCommentCount/$projUsefulLineCount*100));
  }else{
    push @metrics, "0%";
  }
  push @metricNames,"Useful Comment Density";
  push @metrics,$classCount;
  push @metricNames,"Classes";
  push @metrics,$fileCount;
  push @metricNames,"Files";
  if ($fileCount){
    push @metrics, (sprintf("%.1f%",$overlyComplexFile*100/$fileCount));
    push @metricNames, "Overly Complex Files";
  }
  if ($coreGroup && $cyclicGroups{$largestGroupID}{size}){
    push @metrics, (sprintf("%.1f%",$overlyComplexCoreFile*100/$cyclicGroups{$largestGroupID}{size}));
    push @metricNames, "Overly Complex Core Files";
  }
  if ($mGroupSize{Core}){
    push @metrics, (sprintf("%.1f%",$overlyComplexCentralFile*100/$mGroupSize{Core}));
    push @metricNames, "Overly Complex Central Files";
  }
  
  
  #Create the html report
  printprogress($report,.98,"Formatting Output");

  #Export the matrix info to the specified html file
  add_progress($report,.01,"Creating HTML Report");
 
  my $infoString;
  $infoString .=  "var nodes=[";
  my @outputStrings;
  foreach my $file (@fileObjList){
    my $string;
    $string .="{\"name\":\"".cleanJSONString($file->{name})."\"";
    $string .=",\"componentM\":\"".cleanJSONString($file->{componentM})."\"";   
    $string .=",\"componentCP\":\"".cleanJSONString($file->{componentCP})."\""  if $file->{componentCP};
    $string .=",\"alphaOrder\":".$file->{id};
    $string .=",\"medianOrder\":".$file->{medianOrder};
    $string .=",\"coreOrder\":".$file->{coreOrder} if  $coreGroup;
    $string .=",\"group\":".$file->{group} if $file->{group};
    $string .="}";
    push @outputStrings, $string;
  }
  $infoString .=   join( ",", @outputStrings );
  $infoString .=   " ];\n";
 
  #dependency links
  $infoString .=   "var links=[";
  @outputStrings=();
  for(my $row = 0; $row < $fileCount; $row++) {
    for(my $col = 0; $col < $fileCount; $col++) {
      if ($designStructureMatrix[$row][$col]){
        push @outputStrings,"{\"source\":$row,\"target\":$col,\"value\":1}";
      }
    }
  }
  $infoString .=   join( ",", @outputStrings );
  $infoString .=     "];\n";
  
  #Directory info
  $infoString .=   "var directories=[";
  @outputStrings=();
  foreach my $dir (sort {$directoryList{$a}{"first"} <=> $directoryList{$b}{"first"};} keys %directoryList){
    push @outputStrings,"{\"dirName\":\"$dir\",\"first\":".$directoryList{$dir}{"first"}.",\"size\":".$directoryList{$dir}{"size"}."}";
  }
  $infoString .=   join( ",", @outputStrings );
  $infoString .=     "];\n";
  
  #Group Sizes
  $infoString .= makeJavaScriptHash(\%mGroupSize,"mGroupSize");
  $infoString .= makeJavaScriptHash(\%cpGroupSize,"cpGroupSize")if  $coreGroup;
  
  my $i=0;
  $infoString .=   "var metrics=[";
  @outputStrings=();
  foreach my $metric(@metrics){
     push @outputStrings,"{\"name\":\"$metricNames[$i]\",\"value\":\"".$metrics[$i]."\",\"order\":".$i."}";
    $i++;
  }
  $infoString .=   join( ",", @outputStrings );
  $infoString .=     "];\n";
  $infoString .= "var version=\"$version\"\n";


  my $fileString = htmlfile();
  $fileString =~ s/<<EXTERNALDATA>>/$infoString/;

  
  my $htmlFile = $outputDir.$slash."index.html";
  open (FILE,'>',$htmlFile) || die ("Couldn't open $htmlFile $!\n");
  print FILE  $fileString ;
  close FILE;
  


  #Create the XML file for adding Architectures
  if ($createArch){
    my %groups;
    foreach my $file (@fileObjList){
      push(@{$groups{Median}{$file->{componentM}}},$file);
      push(@{$groups{Core}{$file->{componentCP}}},$file) if $file->{componentCP};
    }

    #create arch xml file for Median
    my $medianxml;
    $medianxml .= "<!DOCTYPE arch><arch name=\"Median\">\n";
    foreach my $group (keys %{$groups{Median}}){
      $medianxml .= " <arch name=\"$group\">\n";
      foreach my $file (@{$groups{Median}{$group}}){
        $medianxml .= '   c'.$file->{longname}.'@file='.$file->{longname}."\n";
      }
      $medianxml .= " </arch>\n"
    }
    $medianxml .= "</arch>\n";

    $outputFileName = $outputDir.$slash."arch_median.xml";
    open (FILE,'>',$outputFileName) || die ("Couldn't open $outputFileName $!\n");
    print FILE  $medianxml ;
    close FILE;
    
    my $cpxml;
    if  ($coreGroup){
      my $cpxml;
      $cpxml .= "<!DOCTYPE arch><arch name=\"Core-Periphery\">\n";
      foreach my $group (keys %{$groups{Core}}){
        $cpxml .= " <arch name=\"$group\">\n";
        foreach my $file (@{$groups{Core}{$group}}){
          $cpxml .= '   c'.$file->{longname}.'@file='.$file->{longname}."\n";
        }
        $cpxml .= " </arch>\n"
      }
      $cpxml .= "</arch>\n";
      $outputFileName = $outputDir.$slash."arch_core.xml";
      open (FILE,'>',$outputFileName) || die ("Couldn't open $outputFileName $!\n");
      print FILE  $cpxml ;
      close FILE;
    }
    

  }

  printprogress($report,.99,"Report Finished\n");

  #Final Metrics
  my $i=0;
  foreach my $metric(@metrics){
    $report->print($metricNames[$i].": ".commafy($metrics[$i])."\n");
    $i++;
  }
  
      #Export the project level metrics
  if($createMetricsFiles){
      my $csvString = "Metric Name, Value\n";
      my $i=0;
      foreach my $metric(@metrics){
        $csvString .= '"'.$metricNames[$i].'","'. ($metrics[$i]?commafy($metrics[$i]):'0').'"'."\n";
        $i++;
      }
      my $csvFile = $outputDir.$slash."projectMetrics.csv";
      open (FILE,'>',$csvFile) || die ("Couldn't open $csvFile $!\n");
      print FILE  $csvString ;
      close FILE;
  }
  
  
  my $end_run = time();
  my $run_time = $end_run - $start_run;
  
  $report->print("\n\nReport took $run_time second(s) to run\n");
  $report->print("HTML Report located at $htmlFile\n");
  if ($^O =~ /MSWIN32/i){
    system "start \"\" \"$htmlFile\""; #Extra quotes needed for odd Windows bug
  }
}

#******************** Helper Subroutines  ********************
#show relative progress
sub add_progress{
  my $report = shift;
  my $val = shift;
  my $text = shift;
  $percentComplete += $val;
  printprogress($report,$percentComplete,$text);

}

#Remove special characters from a json string
sub cleanJSONString{
  my $string = shift;
  #escape json special chars
  $string =~ s|\\|\\\\|g; 
  $string =~ s|\/|\\\/|g;
  $string =~ s|"|\\"|g;
  return $string;
}

#Correctly apply commas to numeric strings
sub commafy {
  my $input = shift;
  $input = reverse $input;
  $input =~ s<(\d\d\d)(?=\d)(?!\d*\.)><$1,>g;
  return reverse $input;
}

#Returns the number of external methods/functions called from within this class
sub getCalledMethodCount{
  my $class = shift;
    my $depends = $class->depends;
    my %calledMethods;
    my $called = 0;
    if ($depends){
      my @depRefs = $depends->values();
      foreach my $defref (@depRefs){
        next unless $defref->kind->check("call");
        next unless $defref->ent->kind->check("method, function");
        next if $calledMethods{$defref->ent->id};
        $calledMethods{$defref->ent->id}=1;
        #print "\t".$defref->scope->name."(".$defref->scope->id.") ".$defref->kind->longname()." of ".$defref->ent->name."(".$defref->ent->id.") at line ".$defref->line."\n";
      }
      $called = scalar keys %calledMethods;
    }
    return $called;
}


# return declaration ref (based on language) or 0 if unknown
sub getDeclRef{
   my ($ent) =@_;
   my @decl=();
   my $language = $ent->language();
   return @decl unless defined ($ent);
   
   if ($language =~ /ada/i)
   {
      my @declOrder = ("declarein ~spec ~body ~instance ~formal ~incomplete ~private ~stub",
                 "spec declarein",
                 "body declarein",
                 "instance declarein",
                 "formal declarein",
                 "incomplete declarein",
                 "private declarein",
                 "stub declarein");
               
      foreach my $type (@declOrder)
      {
         @decl = $ent->refs($type);
         if (@decl) { last;  }
      }
   }
   elsif ($language =~ /fortran/i)
   {
      @decl = $ent->refs("definein");
      if (!@decl) {   @decl = $ent->refs("declarein");  }
   }
   else # C/C++
   {
      @decl = $ent->refs("definein");
      if (!@decl) {   @decl = $ent->refs("declarein"); }
   }
   
   if (@decl)
   {   return $decl[0];   }
   else
   {   return 0;   }
}



sub usefulCommentCount(){
  my $file = shift; 
  my $lexer = shift;
  return unless $lexer;
  my $usefulCommentLineCount = 0;
  my @keywords = qw(and_eq asm auto bitand bitor bool case catch char class compl const const-cast continue default delete double dynamic_cast enum exit explicit extern false float fprintf friend goto inline int long mutable namespace new not_eq operator or_eq private protected public register reinterpret-cast short signed sizeof static static_cast struct switch template throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t xor xor_eq);
  my $commentRegexp = '^/\*|^//|\*/$';
  my @strongKeywordsRegExp = ('for\s*\(' , 'while\s*\(' , 'if\s*\(');
  my @preProc = ("#include", "#define", "#endif","#ifndef", "#ifdef", "#undef");
  my @strongLineEnds = (";","{");
  my @maybeLineEnds	= (")");
  my $multiRatio = .4;
  
  #Language overrides
  if ($file->kind->check('java file')){
    @keywords = qw (abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float goto implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient try void volatile);
    $commentRegexp = '^/\*\*|^/\*|^//|\*/$';
    @preProc  = ();
  }elsif ($file->kind->check('web file')){
    @keywords = qw (abstract array as break case catch class clone const continue default delete die do echo else elseif empty endfor endforeach endif endwhile eval exit extends false final finally foreach function global implements import in include include_once instanceof interface isset list long namespace new null print private protected public require require_once return static switch this throw true try typeof unset use var void with);
    $commentRegexp = '^/\*|^//|\*/$|^#|^<!--';
  }elsif($file->kind->check('ada file')){
    @keywords = qw (array begin body case constant delay else elsif end exception exit function generic limited loop mod new not null of others out package private procedure raise range record renames return subtype then type use when with);
    $commentRegexp = '^--';
  }elsif ($file->kind->check('fortran file')){
    @keywords = qw (allocatable allocate block call case character close contains continue cycle deallocate default do else elsewhere end exit external file format function go implicit inquire integer intent logical loop module none nullify only open optional out parameter pointer private program public read real recursive result return rewind save select stop subroutine target then type use where write);
    $commentRegexp = '^!--';
  }elsif ($file->kind->check('python file')){
    @keywords = qw (assert break class continue def del elif else except false finally from global import lambda none not or pass raise return true try yield =);
    $commentRegexp = '^#';
    @strongLineEnds = (")");
  }

  
  $currentLexeme = $lexer->first;
  return unless $currentLexeme;
  my $comment = nextComment($commentRegexp);
  LEXEME:while ($currentLexeme){
    #Yield to GUI interupts
    return if $abort_called;
    Understand::Gui::yield();
    
    #Test and see if the comment is for copyright or licensing
    if ($comment =~ /copyright|license|©/i){
     #print $commentStartLine.":$comment\n" if $verbose;
     next LEXEME;
    }

    
	my $isCode = 0;
	my $maybeCode =0;
	my $lineNum=$commentStartLine;
	my $codeLine=0;
  my $strict = 0;
	#consider each line of the comment separately
	LINE:foreach my $line (split('\n',$comment)){
		my ($strongCode, $strongEnd,$weakCode, $weakEnd,$preproc);
		$line =~ s/^\s+//; #trim leading whitespace
		$line =~ s/\s+$//; #trim trailing whitespace
    $line =~ s/\s+/ /; #collapse large whitespace
    if (length($line) <= 3){
      #print "$lineNum: $line\n" if $verbose;
      next LINE;
    }
		
		#Test for preprocessors in comments
		foreach my $word (@preProc){
			$preproc = 1 if $line =~ /\Q$word/;
		}
		
		#Test for strong keyword match
		foreach my $test (@strongKeywordsRegExp){
			$strongCode = 1 if $line =~ /(?<!\w)$test/;
		}	
		
		#Test the comment line has a strong line/statement ending
		foreach my $char (@strongLineEnds){
			$strongEnd = 1 if $line =~ /\Q$char\E$/;
		}
		
		#Test the comment line has a weak line/statement ending
		foreach my $char (@maybeLineEnds){
			$weakEnd = 1 if $line =~ /\Q$char\E$/;
		}
		
		#Test that the comment line has weak statements
		foreach my $word (@keywords){		
			$weakCode = 1 if $line =~ /(?<!\w)\Q$word\E(?!\w)/;
		}
		if($strict){
      		$isCode = 1 if $preproc || $strongCode || $strongEnd;
      		$isCode =1 if $weakCode && $weakEnd;
      		$maybeCode ++ if ($weakCode || $weakEnd) && ! $isCode;
      
    	}else{
      		$isCode = 1 if $preproc;
      		$isCode = 1 if $strongCode && ($strongEnd || $weakEnd);
      		$isCode = 1 if $weakCode && $strongEnd;
      		$maybeCode++ if $weakCode && $weakEnd;
    	}
		
    	$codeLine= $lineNum if $isCode;
      if ($isCode){
        #print "$lineNum: $line\n" if $verbose;
        $isCode = 0;
        next LINE;
      }
    $usefulCommentLineCount++;
    
    }continue{
      $lineNum++;
    }
  }continue{
    $comment = nextComment($commentRegexp);
  }
  return $usefulCommentLineCount;
}

sub uselessLineCount(){
  my $file = shift; 
  my $lexer = shift;
  return unless $lexer;
  my $thisLex = $lexer->first;
  return unless $thisLex;
  
  my $line = '';
  my $uselessCount = 0;
  while ($thisLex){
    if ($thisLex->text =~ /\n/){
      #Process Line
      $line =~ s/\s//g; #remove whitespace
      if ($line =~ /^[\{\};\(\)]+$/){ 
        $uselessCount++;
      }
      $line = '';
    }elsif ($thisLex->token !~ /Comment/){
      $line .= $thisLex->text;
    }
  }continue{
    $thisLex = $thisLex->next;
  }
  return $uselessCount;
}

sub nextComment(){
  my $commentRegexp = shift;
  while ($currentLexeme && ($currentLexeme->token ne "Comment" || $currentLexeme->inactive())){
    $currentLexeme = $currentLexeme->next;
  }
  return unless $currentLexeme;
  $commentStartLine = $currentLexeme->line_begin;
  my $commentText = $currentLexeme->text;
  $commentText =~ s/$commentRegexp//g; #Strip comment characters
  
  #Sitting on a Comment, let's see if there is another single line comment after it.
 
  while ($currentLexeme->text !~ /\n/ && $currentLexeme->next && $currentLexeme->next->token eq "Newline"
      && $currentLexeme->next->next && $currentLexeme->next->next->token eq "Comment" && $currentLexeme->next->next->text !~ /\n/){
        $currentLexeme = $currentLexeme->next->next;
        my $text = $currentLexeme->text;
        $text =~ s/$commentRegexp//g; #Strip comment characters
        $commentText .= "\n".$text;
      }
  $currentLexeme = $currentLexeme->next;
  return $commentText;
}

#Read through each file with a lexer and store a hash for each chunk of text based off the minimums
sub makeDuplicateCodeHash(){
  my $fileEnt = shift;
  my $lexer = shift;
  return unless $lexer && $fileEnt;
  
  
  my $lex = $lexer->first();
  my @lines;
  my $linenum;
  while ($lex){
    $linenum = $lex->line_begin;
    if ($lex->token !~ /Comment|Newline|Whitespace/){
      $lines[$lex->line_begin].=$lex->text;
    }
    $lex=$lex->next;
  }
  foreach (@lines){$_ =~ s/^\s*|\s*$//g;}
  for(my $i=0;$i<$#lines-($minDupLines);$i++){
    my $line = $lines[$i];
    next unless $line;
    next if $line =~ /^[\{\};\(\)]+$/;  #useless line
    next if $line =~ /^\s*#include|^\s*import/i; #Ignore include/import lines
    for (my $j=1;$j<$minDupLines;$j++){
      $line.= $lines[$i+$j]
    }
    $line =~ s/^\s*|\s*$//g;

    if (length($line)>= $minDupChars){
      $codeHashes{$line} = new Match($line, $minDupLines) unless $codeHashes{$line};
      $codeHashes{$line}->addLoc($fileEnt, $i)
    }
  }  
}

#Clean up the duplicates from the codehash list
sub removeDuplicates{
  my %dupList;
  my @finalList;
  my $counter = 0;
  foreach my $match (sort{$b->getNumLines() <=> $a->getNumLines();} @matches){
    my $i = 0;
    LOC:while($i<$match->getLocCount){
      next LOC if $match->removeDuplicateLocations(\%dupList,$i);
      my ($file,$line) = $match->getLoc($i);
      foreach (my $j=0;$j<$match->getNumLines();$j++){
        $dupList{$file->id}{$line+$j}=1;
      }
      $i++
    }
    push @finalList, $match if ($match->getLocCount()>1);
  }
  @matches = @finalList;
}

#Follow the matches to find out exactly how far they go
sub fillMatchValues{
  my @filledMatches;
  my $counter;
  MATCH: foreach my $match (@matches){
  
    my $locCount = $match->getLocCount();
    next MATCH if $locCount < 2;
    
    my @lexArray; #used to keep track of the current location in each location
    my @endArray; #keep track of the last matching lexeme in each location
    
    #load match object with the first code lexeme for each location in the match
    for (my $i=0; $i < $locCount;$i++){
      my $startLex = lexFromLoc($match->getLoc($i));
      next MATCH unless $startLex;
      while ($startLex && $startLex->token =~ /Comment|Whitespace|Newline/){
        $startLex= $startLex->next;
      }
      $match->addLex($i, $startLex) if $startLex;
      $lexArray[$i] = $startLex;
    }

    my $textmatched = 1;
    STEP:while ($textmatched){
      for (my $i =0;$i < @lexArray; $i++){
        my $lex = $lexArray[$i];
        $endArray[$i]=$lex;

        #Goto the next code lexeme
        $lex=$lex->next;
        while ($lex && $lex->token =~ /Comment|Whitespace|Newline/){
          $lex = $lex->next;
        }
        $match->removeLocation($i) unless $lex;
        $lexArray[$i]=$lex;
      }
      map {$textmatched=0 if ! $_ || !$lexArray[0] || $_->text() ne $lexArray[0]->text();} @lexArray;
    }
    #At this point endArray is on the last matching lexeme in each file, @lexArray is undef
    
#Get the actual text from the first file, sans comments
    my ($file, $line) = $match->getLoc(0);
    my $lex =  lexFromLoc($file, $line);
    my $lexer = $lexers{$file->id};
    my @lexemes = $lexer->lexemes($lex->line_begin,$endArray[0]->line_end);
    my @lines;
    my $text;
    my $dupUsefulLineCount;
    foreach my $lex (@lexemes){
      if ($lex->token !~ /Comment|Newline|Whitespace/){
        $lines[$lex->line_begin].=$lex->text;
      }
    }
    foreach my $line (@lines){
      $line =~ s/\s//g; #remove whitespace
      next unless $line;
      next if $line =~ /^[\{\};\(\)]+$/;
      $dupUsefulLineCount++;
      $text .="$line\n";
    }
    $match->update($text,$dupUsefulLineCount);
    push @filledMatches, $match if $match && $match->getNumLines >= $minDupLines ;
  }
  @matches = @filledMatches;
}


sub lexFromLoc{
  my($file,$line) = @_;
  my $lexer = $lexers{$file->id};
  return unless $lexer;
  return $lexer->lexeme($line,0);
}

sub treemapHTML{
return << 'ENDTREEMAPHTML'
<html>
  <head>
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <script type="text/javascript">
      google.charts.load('current', {'packages':['treemap']});
      google.charts.setOnLoadCallback(drawChart);
      function drawChart() {
        var data = google.visualization.arrayToDataTable([
          ['Node', 'Parent', 'Useful Lines', 'Threshold Violations', 'Full Name'],
          ['Project',null,0,0,'Project'],
          ['Peripheral','Project',0,0,'Peripheral'],
          ['Shared','Project',0,0,'Shared'],
          ['Core','Project',0,0,'Core'],
          ['Control','Project',0,0,'Control'],
          ['Isolate','Project',0,0,'Isolate'],
          ['Central','Project',0,0,'Central'],
          <<TREEMAPDATA>>
        ]);

        tree = new google.visualization.TreeMap(document.getElementById('chart_div'));

        tree.draw(data, {
          minColor: '#9ecae1',
          maxColor: '#084594',
          midColor: '#5388BB',
          headerHeight: 15,
          fontColor: 'black',
          showScale: true,
          useWeightedAverageForAggregation: true,
          generateTooltip: showFullTooltip,
          maxDepth: 2
        });
        
        function showFullTooltip(row, size, value) {
          if (data.getValue(row, 1) == "Project" || data.getValue(row, 1) == null){
            return '<div style="background:#fd9; padding:10px; border-style:solid">' +
           '<span style="font-family:Courier"><b>' + data.getValue(row, 0)+'</span></div>';
          }
          return '<div style="background:#fd9; padding:10px; border-style:solid">' +
           '<span style="font-family:Courier"><b>' + data.getValue(row, 4) +
           '</b>, ' + data.getValue(row, 1) + '</span><br>' +
           'Useful Lines of Code: ' + data.getValue(row,2) + '<br>'+
           'Threshold Violations: ' + data.getValue(row,3) + '<br></div>';
        }

      }
    </script>
  </head>
  <body>
    <div id="chart_div" style="width: 1024px; height: 768px;"></div>
    Left click a node to Zoom In. Right Click to Zoom Out.
  </body>
</html>
ENDTREEMAPHTML

}

#This is the text that gets sent to the html output file, <<EXTERNALDATA>> gets replaced with project specific data
sub htmlfile{

return << 'ENDHTMLDOC'
<!DOCTYPE html>
<script>
<<EXTERNALDATA>>



// **************Everything below this line is template that needs to not have project specific information****************************
</script>
<style>

:root {
  --main-bg-color: #CFE8EF;
  --dark-bg-color: #C6DBF0;
  --extra-dark-bg: #AED1E6;
  --font-color: #3B5863;
  --border: 1px solid #85C7DE;
  color: var(--font-color);
  font-family:arial;
}

#topbox{
  height:auto;
  background-color: var(--main-bg-color);
  border-radius: 10px;
  border: var(--border);
  max-width:960px;
  margin:0px auto;

}

#topbox div{
  text-align:center;
}

#topbox-container {
  width:100%;
  position:fixed;
  top:0px;
  height:auto;
  z-index: 100;
}

input[type=range] {
  -webkit-appearance: none;
  width: 200px;
  background-color: var(--extra-dark-bg);
}

select{
  background-color: var(--extra-dark-bg);
}

select option {
  background-color: var(--extra-dark-bg);
}
#pageTitle{
  text-align:center;
  margin: 5px;
}

.controller{
  display: inline-block;
  text-align: center;
}

button{
  background-color: var(--extra-dark-bg);
  border-radius: 8px;
}
#zoomtag{
  display: inline-block; 
  width:3em;
}


body{
  position:absolute;
  overflow:auto;
}
.graphContainer {
  padding: 10px;
  margin: auto;
  width:100%;
  position:relative;
}

#myCanvas{
  padding-left: 0;
  padding-right: 0;
  margin-left: auto;
  margin-right: auto;
  display: block;
  z-index: 2;
}

.metrics{
  border-radius: 10px;
  width: 170px;
  border: var(--border);
  padding: .5em;
  padding-top:0em;
  background-color: var(--main-bg-color);
  margin: 0 auto;
  position:fixed;
  left:0;
  top:25%;
  z-index: 90;
  line-height:110%
}

.metricsTitle{
  padding:2px;
  margin: 0px;
  text-align: center;
}

.metricName{
  font-weight:bold;
  background-color: var(--dark-bg-color);
  width:100%;
}

.metricVal{
  text-align:right;
}

#hoverInfo{
  height:2.5em;
}

#description{
  max-width:960px;
  margin: auto;
  text-align:center;
  background-color:var(--main-bg-color);
  border:var(--border);
  border-radius: 10px;
  z-index: 80;
  padding:5px;
}


#description-cont {
  width:100%;
  position:fixed;
  bottom: 0;
  left: 0;
  z-index:0;
}



</style>
<html>
<body onload="draw()" onresize="draw()">
<header>
  <div id="topbox-container">
  <div id="topbox">
      <h1 id="pageTitle" style="">Directory Structure Based Design Structure Matrix</h1>
      <span class=controller style="width:35%"><b>Select Matrix</b> 
        <select id="order" onchange="draw(this.value)">
          <option value="Architect" selected>Architect's View</option>
          <option value="Median">Median Matrix</option>
        </select>
      </span>
      <span class=controller style="width:14%"><button id=metricsbtn onclick="metricsBtnPress()">Hide Metrics</button></span>
      <span class=controller style="width:14%"><button id=descbtn onclick="descBtnPress()">Hide Description</button></span>
      <span class=controller style="width:35%">Zoom:<input name="zoom" type="range" name="points" min="0" max="10"  value="1" oninput="setZoom(this.value)" onchange="setZoom(this.value)" onmouseup="draw()">
        <span id="zoomtag">1X</span>
      </span>
      
      <div id="hoverInfo"></div>
    </div>
  </div>
</header>
<span class="metrics" id="metricspane"></span>


    <div class="graphContainer" id="graphContainer">
    <canvas id="myCanvas" ></canvas>
    </div>
</body>

<footer>
  <div id ="description-cont">
        <div  id="description"></div>
</footer>
<script charset="utf-8">


// Add the Metrics Section
var projName;
var isCorePeriphery =false;
var MetricsHTML = "<h3 class=\"metricsTitle\">Metrics</h3>";
metrics.forEach(function(metricObj){
  if (metricObj["name"] == "Project Name"){
    projName = metrics[0].value;
    return;
    }
  //Add the Core-Periphery graph if it exists.
  if (metricObj["name"] == "Architecture Type" && (metricObj["value"] == "Core-Periphery" || metricObj["value"] == "Borderline Core-Periphery")){
    var x = document.getElementById("order");
    var option = document.createElement("option");
    option.text = "Core-Periphery Matrix";
    option.value ="Core-Periphery";
    isCorePeriphery=true;
    x.add(option);
  }
  var value = metricObj["value"];
  if(!isNaN(value)){
    value=+value;
    value = value.toLocaleString();
  }
  MetricsHTML += "<div class=\"metricName\">"+metricObj["name"]+"</div> <div class=\"metricVal\"> "+ value +"</div>\n";
});
document.getElementById("metricspane").innerHTML =   MetricsHTML;

//Setup ordered node lists for the non-architect views
var medianNodes =[];
var coreNodes = [];
nodes.forEach(function(node){
  medianNodes[node.medianOrder]=node;
  if (isCorePeriphery){
    coreNodes[node.coreOrder]=node;
  }
});

// Setup Global information
var groupOrder = ["Shared","Core","Peripheral","Control","Isolate"];
var nodeColors = {Shared: "#69ad67",Core: "#ea6a66",Peripheral: "#ebebeb",Control: "#ebed62",Isolate: "#eabe62"};
var medianNames ={Shared:"Shared-M",Core:"Central",Peripheral:"Periphery-M",Control:"Control-M",Isolate: "Isolate"};
var baseColor = "#1a12f0";
var backgroundColor = "lightgray";
var gridColor = 'rgba(255,255,255,.5)';//"white";
var outlineColor = 'rgba(0,0,0,.5)';//"black";
var minBorderLineWidth = .5; //Minimum thickness for border lines
var nodeLineWidth;


var CurGraph="Architect";
var scaleRatio;
var canvas = document.getElementById("myCanvas");
var ctx = canvas.getContext("2d");

var zoomLevel=1;
var initFontSize=12;
var numFiles=nodes.length;
var canvasOffset = 0;
var showMetrics=1;
var showDescription=1;
  

  
function draw(graph){
  if (typeof graph != 'undefined'){
    CurGraph=graph;
  }
  
  //Get get Document size info so the image will fit in the current window.
  var bkgWidth = window.innerWidth || document.body.clientWidth;
  var bkgHeight = window.innerHeight || document.body.clientHeight;
  var headerSpace = document.getElementById('topbox-container').offsetHeight;
  var footerSpace = 0;
  if (showDescription){
   footerSpace = 85;
  }
  var metricSpace = 0;
  if (showMetrics){
    metricSpace =   document.getElementById("metricspane").offsetWidth;
  }
  
  var defaultBkgSize = bkgHeight - headerSpace - footerSpace-50;
  //if (defaultBkgSize > 1000)
   // defaultBkgSize = 1000;
  var bkgSize = defaultBkgSize*zoomLevel;
  canvas.width=bkgSize;
  canvas.height=bkgSize;
  document.getElementById("graphContainer").style.height=bkgSize+"px";
  document.getElementById("graphContainer").style.top=headerSpace+"px";
  document.getElementById("graphContainer").style.left=metricSpace+"px";
  document.getElementById("graphContainer").style.marginBottom=footerSpace+"px";
  //ctx.clearRect(0, 0, bkgSize, bkgSize); //clear canvas for redraw
  
  
  //get the size of the largest number label to calculate the offset
  canvasOffset=0;
  var gridLines = getGridLines();
  if (numFiles > 10){
    gridLines.forEach(function(gridNum){
      ctx.font = (initFontSize*zoomLevel)+"px Arial";
      var txtSize = ctx.measureText(gridNum.toLocaleString()).width;
      canvasOffset=Math.max(txtSize,canvasOffset);
    });
  }

  
  //prepare the canvas the graph goes on
  var size = (bkgSize-canvasOffset)
  scaleRatio = size/numFiles;
  
  //calculate line widths
  var borderLineWidth= minBorderLineWidth;
  if (scaleRatio > 1){
    borderLineWidth = minBorderLineWidth*scaleRatio;
    borderLineWidth = Math.min(borderLineWidth,10)
  }
  nodeLineWidth = scaleRatio*.1;

  if (numFiles > 10){
    //Grid Numbers left side
    gridLines.forEach(function(gridNum){
      ctx.textAlign = "right";
      ctx.font = initFontSize*zoomLevel+"px Arial";
      ctx.fillStyle = outlineColor;
      ctx.textBaseline="middle"; 
      ctx.fillText(gridNum.toLocaleString(),canvasOffset,gridNum*scaleRatio+canvasOffset+scaleRatio/2);
    });
    
      //Grid Numbers top
      ctx.save();
      ctx.translate(canvasOffset,canvasOffset);
      ctx.rotate(-Math.PI/2);
      gridLines.forEach(function(gridNum){
        if (gridNum>0){ //We don't want the zero on both axes
          ctx.textAlign = "left";
          ctx.font = (initFontSize*zoomLevel)+"px Arial";
          ctx.fillStyle = outlineColor;
          ctx.textBaseline="middle"; 
          ctx.fillText(gridNum.toLocaleString(),0,gridNum*scaleRatio+scaleRatio/2);
        }
      });
      ctx.restore();
    
    //Move into the inner part of the canvas now for everything else
    ctx.save();
    ctx.translate(canvasOffset,canvasOffset);
  }
  
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0,0,size,size)

  
    if (CurGraph == "Core-Periphery"){
    //Core-Periphery background
    var currentXY=0;
    groupOrder.forEach(function(group){
      if (cpGroupSize[group]){
        ctx.strokeStyle = nodeColors[group];
        ctx.fillStyle = nodeColors[group];
        ctx.lineWidth=borderLineWidth;
        roundRect(ctx,currentXY*scaleRatio,currentXY*scaleRatio,cpGroupSize[group]*scaleRatio,cpGroupSize[group]*scaleRatio,0,true);
        currentXY=currentXY+Number(cpGroupSize[group]);
      }
    });
    //Core-Periphery node
    links.forEach(function(link) {
      ctx.strokeStyle = getNodeColor(nodes[link.target],nodes[link.source],"core");
      ctx.fillStyle = baseColor;
      ctx.lineWidth=nodeLineWidth;
      roundRect(ctx,nodes[link.target].coreOrder*scaleRatio,nodes[link.source].coreOrder*scaleRatio,scaleRatio,scaleRatio,.1,true);
    });
    
    //Core-Periphery border
    var currentXY=0;
    groupOrder.forEach(function(group){
      if (cpGroupSize[group]){
        ctx.strokeStyle = outlineColor;
        ctx.lineWidth=borderLineWidth;
        roundRect(ctx,currentXY*scaleRatio,currentXY*scaleRatio,cpGroupSize[group]*scaleRatio,cpGroupSize[group]*scaleRatio,0,false);
        currentXY=currentXY+Number(cpGroupSize[group]);
      }
    });
    
    //Core-Periphery explanatory text
    document.title=projName+" Core-Periphery Based DSM";
    document.getElementById("pageTitle").innerHTML = projName+" Core-Periphery Based Design Structure Matrix";
    document.getElementById("description").innerHTML = 
    "This project contains a Core group of files in red that much of the system is connected with. The other components are organized based on their relationship with the Core group. "+
    "Each point in the matrix represents a directional dependency relationship between two files. Dependencies above the diagonal are cyclic interdependencies which cannot be reduced."+" (v"+version+")";  
  }
  else if (CurGraph == "Median"){
    //Median Background
    var currentXY=0;
    groupOrder.forEach(function(group){
      if (mGroupSize[group]){
        ctx.strokeStyle = nodeColors[group];
        ctx.fillStyle = nodeColors[group];
        ctx.lineWidth=borderLineWidth;
        roundRect(ctx,currentXY*scaleRatio,currentXY*scaleRatio,mGroupSize[group]*scaleRatio,mGroupSize[group]*scaleRatio,.0,true);
        currentXY=currentXY+Number(mGroupSize[group]);
      }
    });
    
    //Median nodes
    links.forEach(function(link) {
      ctx.fillStyle = baseColor;
      ctx.strokeStyle = getNodeColor(nodes[link.target],nodes[link.source],"median");
      ctx.lineWidth=nodeLineWidth;
      roundRect(ctx,nodes[link.target].medianOrder*scaleRatio,nodes[link.source].medianOrder*scaleRatio,scaleRatio,scaleRatio,.1,true,true);
    });
    
    //Median border
    ctx.lineWidth=borderLineWidth;
    var currentXY=0;
    
    groupOrder.forEach(function(group){
      if (mGroupSize[group]){
        ctx.strokeStyle = outlineColor;
        ctx.lineWidth=borderLineWidth;
        roundRect(ctx,currentXY*scaleRatio,currentXY*scaleRatio,mGroupSize[group]*scaleRatio,mGroupSize[group]*scaleRatio,0,false);
        currentXY=currentXY+Number(mGroupSize[group]);
      }
    });
   
    //Median explanatory text
    document.title=projName+" Median Based DSM";
    document.getElementById("pageTitle").innerHTML = projName+" Median Based Design Structure Matrix";
    document.getElementById("description").innerHTML = 
    "This view places all of the significant cyclic groups together in the red Central component. Components are classified based on the median values of the number of direct and indirect connections. "+
    "Each point in the matrix represents a directional dependency relationship between two files. Dependencies above the diagonal are cyclic interdependencies which cannot be reduced"+" (v"+version+")";

  }
  else{ //Architect View
    //Architect View nodes
    
    links.forEach(function(link) {
        ctx.fillStyle = baseColor;
        ctx.strokeStyle = backgroundColor;
        ctx.lineWidth=nodeLineWidth;
        roundRect(ctx,link.target*scaleRatio,link.source*scaleRatio,scaleRatio,scaleRatio,.1,true,true);
      });
    //Architect View Border
    if (Object.keys(directories).length >1){
      directories.forEach(function(dir){
        ctx.strokeStyle = outlineColor;
        ctx.lineWidth=borderLineWidth;
        roundRect(ctx,dir.first*scaleRatio,dir.first*scaleRatio,dir.size*scaleRatio,dir.size*scaleRatio,0,false);
      });
    }
    
    //Architect View explanatory text
    document.title=projName+" Architect's View DSM";
    document.getElementById("pageTitle").innerHTML = projName+" Architect's View Design Structure Matrix";
    document.getElementById("description").innerHTML = 
    "This is the initial design view. Files are shown organized according to their directory structure, or how the System Architect designed it. "+
    "If file i depends on file j, a mark is placed in the row of i and the column of j"+" (v"+version+")";
  }
  
  if(numFiles > 10){
    //Generate the grid lines
  gridLines.forEach(function(gridNum){
      if (gridNum >0){
        ctx.strokeStyle = gridColor;
        ctx.lineWidth=borderLineWidth;
        ctx.beginPath();
        ctx.moveTo(0,gridNum*scaleRatio)
        ctx.lineTo(size,gridNum*scaleRatio);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(gridNum*scaleRatio,0)
        ctx.lineTo(gridNum*scaleRatio,size);
        ctx.stroke();
      }
    });
  }
    
  //Draw an orgin line
  ctx.strokeStyle = outlineColor;
  ctx.lineWidth= borderLineWidth;
  ctx.beginPath();
  ctx.moveTo(0,0);
  ctx.lineTo(size,size);
  ctx.stroke();
  
 
}


function metricsBtnPress(){
  if (showMetrics ==1){
    showMetrics = 0;
    document.getElementById("metricspane").style.display= "none";
    document.getElementById("metricsbtn").innerHTML= "Show Metrics";
    draw();
  }else{
    showMetrics = 1;
    document.getElementById("metricspane").style.display= "block";
    document.getElementById("metricsbtn").innerHTML= "Hide Metrics";
    draw();
  }
}

function descBtnPress(){
  if (showDescription ==1){
    showDescription = 0;
    document.getElementById("description-cont").style.display= "none";
    document.getElementById("descbtn").innerHTML= "Show Description";
    draw();
  }else{
    showDescription = 1;
    document.getElementById("description-cont").style.display= "block";
    document.getElementById("descbtn").innerHTML= "Hide Description";
    draw();
  }
}

function getGridLines(){
  if (numFiles <= 10){return;}
  var numString = numFiles.toString();
  var strLength = numString.length-1;
  var retNumbers = [];
  var first = parseInt(numString[0]);
 
  for (i = 0;i<= first;i++){
      var tmpNum = (i*Math.pow(10,strLength));
      retNumbers.push(tmpNum);
     
    if (first <= 5){ 
      var tmpNum = (i*10+5) *Math.pow(10,strLength-1)
      if (tmpNum < numFiles){
        retNumbers.push(tmpNum);
      }
    }
  }
  return retNumbers;
}

canvas.addEventListener('mousemove', handleMouseMove, false);
function handleMouseMove(evt){
    var rect = canvas.getBoundingClientRect();
    var absX = evt.clientX - rect.left;
    var absY = evt.clientY - rect.top;
    var mouseX= Math.floor((absX-canvasOffset) / scaleRatio);//  Math.floor((evt.clientX-rect.left-canvasOffset)/(rect.right-rect.left-canvasOffset)*canvas.width/scaleRatio);
    var mouseY= Math.floor((absY-canvasOffset) / scaleRatio);//Math.floor((evt.clientY-rect.top-canvasOffset)/(rect.bottom-rect.top-canvasOffset)*canvas.height/scaleRatio);
    var message="";
    var title = "";
    var currentXY=0;
    var size;
    var selectedGroup;
  
  
  if (CurGraph == "Core-Periphery"){
    groupOrder.forEach(function(group){
      var groupSize = Number(cpGroupSize[group]);
      if (!groupSize){
        return;
      }
      if (mouseX>=currentXY && mouseX<=currentXY+groupSize && mouseY>=currentXY && mouseY<=currentXY+groupSize){
        selectedGroup=group;
        size=groupSize;
      }
      switch(selectedGroup){
        case("Shared"):
          message="<span style=\"color:"+baseColor+"\">Shared components("+size+" Files)  These files are used by many other components, both in and out of the Core.</span>";
          title= "Shared components("+size+" Files)";
          break;
        case("Core"):
          message="<span style=\"color:"+baseColor+"\">Core components("+size+" Files)  Core components. A substantial part of the system is linked to these files.</span>";
          title= "Core components("+size+" Files)";
          break;
        case("Peripheral"):
          message="<span style=\"color:"+baseColor+"\">Peripheral components("+size+" Files)  These files do not interact with the Core</span>";
          title= "Peripheral components("+size+" Files)";
          break;
        case("Control"):
          message="<span style=\"color:"+baseColor+"\">Control components("+size+" Files)  These files make use of other components but are not used by other components</span>";
          title= "Control components("+size+" Files)";
          break;
        case("Isolate"):
          message="<span style=\"color:"+baseColor+"\">Isolated components("+size+" Files)  These files are not connected to any other components.</span>";
          title= "Isolated components("+size+" Files)";
          break;
      }
      currentXY=currentXY+groupSize;
    });
    message =message+"<br>"+coreNodes[mouseY].name+" &rarr;  "+coreNodes[mouseX].name;
  }
  else if (CurGraph == "Median"){
    groupOrder.forEach(function(group){
      var groupSize = Number(mGroupSize[group]);
      if (!groupSize){
        return;
      }
      if (mouseX>=currentXY && mouseX<=currentXY+groupSize && mouseY>=currentXY && mouseY<=currentXY+groupSize){
        selectedGroup=medianNames[group];
        size=groupSize;
      }
     switch(selectedGroup){
      case("Shared-M"):
        message="<span style=\"color:"+baseColor+"\">Shared-M components("+size+" Files) These files are used by many other components, including the Central Components</span>";
        title= "Shared-M components("+size+" Files)";
        break;
      case("Central"):
        message="<span style=\"color:"+baseColor+"\">Central components("+size+" Files)  These files are the main cyclic groups in the program that many other components interact with</span>";
        title= "Central components("+size+" Files)";
        break;
      case("Periphery-M"):
        message="<span style=\"color:"+baseColor+"\">Periphery-M components("+size+" Files)  These files do not interact with the Central components</span>";
        title= "Periphery-M components("+size+" Files)";
        break;
      case("Control-M"):
        message="<span style=\"color:"+baseColor+"\">Control-M components("+size+" Files)  These make use of other components but are not used by other components</span>";
        title= "Control-M components("+size+" Files)";
        break;
      case("Isolate"):
        message="<span style=\"color:"+baseColor+"\">Isolated components("+size+" Files)  These files are not connected to any other components.</span>";
        title= "Isolated components("+size+" Files)";
        break;
    }
    
      currentXY=currentXY+groupSize;
    });
    message =message+"<br>"+medianNodes[mouseY].name+" &rarr;  "+medianNodes[mouseX].name;
  }
  else{ //Architect View
    directories.forEach(function(dir){
      if (mouseX>=currentXY && mouseX<=currentXY+dir.size && mouseY>=currentXY && mouseY<=currentXY+dir.size){
        message="<span style=\"color:"+baseColor+"\">Directory: '"+dir.dirName+" ("+dir.size+" Files)</span>";
        title = dir.dirName+" ("+dir.size+" Files)";
      }
      currentXY=currentXY+dir.size;
    });
    message =message+"<br>"+nodes[mouseY].name+" &rarr;  "+nodes[mouseX].name;
  
  }
  
  canvas.title=title;
  document.getElementById("hoverInfo").innerHTML = message;
}

function setZoom(newZoom){
  if (newZoom == 0){
    newZoom = "1/2";
    zoomLevel=.5;
  }else{
    zoomLevel=newZoom;
  }
  document.getElementById("zoomtag").innerHTML = newZoom+"X";
  //draw();
}
/**
 * Draws a rounded rectangle using the current state of the canvas.
 * If you omit the last three params, it will draw a rectangle
 * outline with a 5 pixel border radius
 * @param {CanvasRenderingContext2D} ctx
 * @param {Number} x The top left x coordinate
 * @param {Number} y The top left y coordinate
 * @param {Number} width The width of the rectangle
 * @param {Number} height The height of the rectangle
 * @param {Number} radius What percent of the rectangle should curve (in decimal)
 * @param {Boolean} [fill = false] Whether to fill the rectangle.
 * @param {Boolean} [stroke = true] Whether to stroke the rectangle.
 */
function roundRect(ctx, x, y, width, height, radius, fill, stroke) {
  if (typeof stroke == 'undefined') {
    stroke = true;
  }
  if (typeof radius === 'undefined') {
    radius = .1;
  }
  if (width < .1 || height < .1){
    ctx.fillRect(x,y,width,height);
  }else{
    radius = radius * width;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    if (fill) {
      ctx.fill();
    }
    if (stroke) {
      ctx.stroke();
    }
  }

}

 function getNodeColor(node1,node2,type){
    var comp1,comp2;
    var color =  backgroundColor;
    if (type == "core"){
      comp1 = node1.componentCP;
      comp2 = node2.componentCP;
    }else{
      comp1 = node1.componentM;
      comp2 = node2.componentM;
    }
    if (comp1 == comp2){
      color = nodeColors[comp1];
    }
    return color;
  }
</script>




ENDHTMLDOC
}

#This creates the script options
sub init {
  my $report = shift;
  $abort_called=0; #reset the cancel flag in case it was set on another run
  $report->option->directory("outputDir","Specify output directory","");
  $report->option->integer("MaxFileSize","Maximum Recommended File Size (ULOC)",200);
  $report->option->integer("MaxCBOThreshold",     "Maximum Recommended Coupling Between Object Classes (CBO)",8);
  $report->option->integer("MaxWMC",     "Maximum Recommended Weighted Methods per Class(WMC)",12);
  $report->option->integer("MaxWMCM",    "Maximum Recommended Weighted Methods per Class with McCabe(WMC-McCabe)",100);
  $report->option->integer("MaxRFC",     "Maximum Recommended Response for Class(RFC)",30);
  $report->option->integer("DuplicateMinLines","Minimum numbers lines to count as duplicate code",5);
  $report->option->integer("DuplicateMinChars","Minimum numbers characters to count as duplicate code",20);
  $report->option->checkbox("createTestFiles","Generate validation files for testing",0);
  $report->option->checkbox("createArch",     "Generate Architecture import files",1);
  $report->option->checkbox("createMetrics",  "Generate metrics csv files",1);

  }

#return the longest item from a list
sub longestItem {
    my $max = -1;
    my $max_ref;
    for (@_) {
        if (length > $max) {  # no temp variable, length() twice is faster
            $max = length;
            $max_ref = \$_;   # avoid any copying
        }
    }
    $$max_ref
}

# Turn a hash into the text for a javascript hash
sub makeJavaScriptHash(){
  my $hashVal = shift;
  my $name = shift;
  
  my @outputStrings=();
  my $infoString = "var $name={";
  foreach (sort keys %{$hashVal}){
    push @outputStrings, "$_:\"$hashVal->{$_}\"";
  }
  $infoString .=   join( ",", @outputStrings );
  $infoString .= "};\n";
  return $infoString;

}

#Return the median value of an array
sub median{
    my @vals = sort {$a <=> $b} @_;
    my $len = @vals;
    if($len%2) #odd?
    {
        return $vals[int($len/2)];
    }
    else #even
    {
        return ($vals[int($len/2)-1] + $vals[int($len/2)])/2;
    }
}


# Print a Square Matrix to the specific text file
sub printSquareMatrix{
  my $firstColumnListRef = shift;  #ref to a list of titles to be printed before the matrix
  my $matrixRef = shift; #ref to the matrix that will be printed
  my $fileName = shift; #if specified send the output to the file - recommended
  
  my @firstColumnList = @{$firstColumnListRef};
  my $length = length longestItem(@firstColumnList);
  
  if ($fileName){
    open (FILE,'>',"$fileName") || die ("Couldn't open $fileName $!\n");
  }
  my @matrix = @{$matrixRef};
  for(my $row = 0; $row < scalar @firstColumnList; $row++) {
    my $printString = sprintf("%${length}s ", $firstColumnList[$row]);
    for(my $col = 0; $col < scalar @firstColumnList; $col++) {
      my $val = "0";
      $val = 1 if $matrix[$row][$col];
      $printString.="$val";
    }
    print FILE $printString."\n" if $fileName;
    print $printString."\n" unless $fileName;
  }
  close FILE if $fileName;
}

#Ouput the progress
sub printprogress{
  my $report = shift;
  my $percent = shift;
  my $text = shift;
  $percentComplete = $percent;
  my $printPercent = sprintf("%.1f",$percent*100);
  $report->progress($printPercent,"$printPercent% - $text");
}

#Sort the Core Periphery group using the specicied criteria
sub sortByCorePeriphery{
  if ($a->{componentCP} ne $b->{componentCP}){
    if ($a->{componentCP} eq "Shared"){return -1}
    if ($b->{componentCP} eq "Shared"){return 1}
    if ($a->{componentCP} eq "Core"){return -1}
    if ($b->{componentCP} eq "Core"){return 1}
    if ($a->{componentCP} eq "Peripheral"){return -1}
    if ($b->{componentCP} eq "Peripheral"){return 1}
    if ($a->{componentCP} eq "Control"){return -1}
    if ($b->{componentCP} eq "Control"){return 1}
    #Should not get here since both would have to be  "isolate"
  }
  if ($a->{componentCP} eq $b->{componentCP}){
  # Same components, sort by VFI Desc then VFO asc
  return $b->{vfi} <=> $a->{vfi} || $a->{vfo} <=> $b->{vfo}
  }
}

#Sort the Median goup using the specicied criteria
sub sortByMedian{
  if ($a->{componentM} ne $b->{componentM}){
    if ($a->{componentM} eq "Shared"){return -1}
    if ($b->{componentM} eq "Shared"){return 1}
    if ($a->{componentM} eq "Core"){return -1}
    if ($b->{componentM} eq "Core"){return 1}
    if ($a->{componentM} eq "Peripheral"){return -1}
    if ($b->{componentM} eq "Peripheral"){return 1}
    if ($a->{componentM} eq "Control"){return -1}
    if ($b->{componentM} eq "Control"){return 1}
    #Should not get here since both would have to be  "isolate"
  }
  if ($a->{componentM} eq $b->{componentM}){
  # Same components, sort by VFI Desc then VFO asc
  return $b->{vfi} <=> $a->{vfi} || $a->{vfo} <=> $b->{vfo}
  }
}

#Recursivly go through the dependency tree for the given node and add its indirect dependencies
#Makes use of Tarjan's strongly connected components algorithm to handle cycles
sub strongconnect(){
  my $report=shift;
  my $v = shift;
  $v->{index}=$index;
  $v->{lowlink}=$index;
  $index++;
  push @stack, $v;
  $v->{onstack}=1;
 
  my @deps = ($v->{entid});
  #Consider successors of v
  foreach my $wID (@{$v->{depends}}){
    return if $abort_called;
    Understand::Gui::yield();
    my $w = $fileObjsByEntID{$wID};
    if($w->{index}){
      push @deps, @{$w->{indirect}};
    }
    if(! $w->{index}){
      # Successor w has not yet been visited; recurse on it
      push @deps, strongconnect($report,$w);
      $v->{lowlink} = min ($v->{lowlink}, $w->{lowlink});
    }elsif ($w->{onstack}){
      #Successor w is in stack S and hence in the current SCC
      $v->{lowlink} = min ($v->{lowlink}, $w->{index});
    }
  }
  
  
  my @strongGraph;
  my $w;
  #If v is a root node, pop the stack and everything on it is strongly connected
  if ($v->{lowlink} == $v->{index}){
    do{
      $w = pop @stack;
      $w->{onstack}=0;
      push @strongGraph, $w;
      push @deps, $w->{entid};
      foreach (@{$w->{depends}}){
        push @deps, $_;
      }
    }while ($w->{id} != $v->{id});
   
  }
   my %depHash;
    foreach (@deps){
      $depHash{$_}=1 if $_;
    }
    @deps = keys %depHash; 
    foreach my $dep (@deps){
      push @strongGraph, $v unless @strongGraph;
      foreach $w (@strongGraph){
        $visibilityMatrix[$w->{id}][$fileObjsByEntID{$dep}->{id}] = 1;
        push @{$w->{indirect}},$dep;
      }
    }
    $analyzedCount++;
    add_progress($report,(.7*10/$fileCount),"Calculating Transitive Closure") unless $analyzedCount%10;
    return @deps;
}


#********************* Conversion Functions *********************

sub openDatabase($){
    my ($dbPath) = @_;

    my $db = Understand::Gui::db();

    # path not allowed if opened by understand
    if ($db&&$dbPath) {
  die "database already opened by GUI, don't use -db option\n";
    }

    # open database if not already open
    if (!$db) {
  my $status;
  print usage("Error, database not specified\n\n") && exit() unless ($dbPath);
  ($db,$status)=Understand::open($dbPath);
  die "Error opening database: ",$status,"\n" if $status;
    }
    return($db);
}

sub closeDatabase($){
    my ($db)=@_;

    # close database only if we opened it
    $db->close() if $dbPath;
}

sub usage($) {
    my $string =  shift(@_) . <<"END_USAGE";
Usage: $0 -db database
  -db database  Specify Understand database (required for uperl, inherited from Understand)
END_USAGE
  foreach my $opt (keys %{$report->option()} ){
    next if $opt eq "db";
    $string .= "  -$opt";
    $string .= " ".$report->option->{$opt}{kind} if $report->option->{$opt}{kind} ne "boolean";
    $string .= "    ".$report->option->{$opt}{desc}."\n";
    my $choices = $report->option->{$opt}{choices};
    $string .= "        Valid Options: ".join(',',@$choices)." \n" if $choices;
    $string .= "        Defaults To : ".$report->option->{$opt}{default}."\n" if $report->option->{$opt}{default};
  }
  print $string;
}

sub setupOptions(){
  my @optList;
  push @optList,"db=s";
  push @optList,"help";
  foreach my $opt (keys %{$report->option()}){
    my $string = $opt;
    $opt .= "=s" if $report->option->{$opt}{kind} ne "boolean";
    push @optList,$opt;
  }
  GetOptions(\%options,@optList);
  $dbPath = $options{db};
  $help = $options{help};
  foreach my $opt (keys %options){
    next if $opt eq "db";
    next if $opt eq "help";
    $report->option->set($opt,$options{$opt});
  }
  # help message
  print usage("") && exit () if ($help);
  # open the database
  my $db=openDatabase($dbPath);
  $report->db($db);
}

#*******************************Packages**********************************************
package convertIreport;
use strict;

sub new {
   my($class) = @_;
   my $self = bless({}, $class);
    return $self;
  }

# Return the database associated with the report.
sub db {
    my $report = shift;
    my $db = shift;
    $report->{db}=$db if $db;
    return $report->{db};
}
sub bgcolor {}
sub bold {}
sub entity {}
sub fontbgcolor {}
sub fontcolor {}
sub hover {}
sub italic {}
sub nobold {}
sub noitalic {}
sub print {
    my $report = shift;
    my $text = shift;
    my $treeDepth = $report->{depth};
    my $prestring;
    my $poststring;
    if ($treeDepth){
      $prestring = "|"x($treeDepth-1);
      $poststring="\n";
    }
    #print $prestring.$text.$poststring;
}
sub progress {}
sub syncfile {}
sub tree {
    my $report = shift;
    my $depth = shift;
    my $expand = shift;
    $report->{depth}=$depth;
}
sub option {
    my $report = shift;
    if (! $report->{opt}){
      $report->{opt} =  convertOption->new($report);
    }
    return $report->{opt};
}

1;
package convertOption;
use strict;

# Class or object method. Return a new report object.
sub new {
   my($class, $db) = @_;
   my $self = bless({}, $class);
   $self->{db} = $db;
    return $self;
}


sub checkbox       {
  my ($self, $name, $desc )=@_;
  $self->{$name} = { 
    desc => $desc,
    variable => "opt_$name",
    kind  => "boolean",
  };
}

sub checkbox_horiz {choice(@_);}
sub checkbox_vert  {choice(@_);}
sub choice{
  my ($self, $name, $desc, $choices, $default )=@_;
  $self->{$name} = { 
    desc => $desc,
    variable => "opt_$name",
    kind  => "choice",
    choices => $choices,
    default => $default,
    setting => $default,
  };
}
sub directory      { text(@_,"directory");}
sub file           { text(@_,"file");}
sub integer        { text(@_,"integer");}
sub label          { text(@_,"label");}
sub lookup         {
  my ($self, $name ) = @_;
  return $self->{$name}{setting};
}
sub radio_horiz    {choice(@_);}
sub radio_vert     {choice(@_);}
sub set{
  my ($self, $name, $value) = @_;
  $self->{$name}{setting} = $value;
}
sub text{
  my ($self, $name, $desc,$default, $kind) = @_;
  $kind = "text" unless $kind;
  $self->{$name} = { 
    desc => $desc,
    variable => "opt_$name",
    kind  => $kind,
    default => $default,
    setting => $default,
  };
}

1;
#*******************************Core Packages**********************************************
package fileObj;
sub new{
  my $class = shift;
  my $id = shift;
  my $ent = shift;
  my $hasClasses = $ent->filerefs("define","class ~function",1);
  my $depends = $ent->depends();
  my $dependCount = 0;
  $dependCount = $depends->keys() if $depends && ! $hasClasses;
  my $funcCalls = 0;
  $funcCalls = $ent->filerefs("call, use",$funcKindString,1)  if ! $hasClasses;
  my $declFuncs = 0;
  $declFuncs = $ent->metric("CountDeclFunction") + $ent->metric("CountDeclSubProgram") if ! $hasClasses;
  my $maxCyclo = 0;
  $maxCyclo = $ent->metric("maxcyclomatic") if ! $hasClasses;
  my $self = {
    analyzed => 0,
    class => '',
    commentToCode => '',
    componentCP => '',
    componentM => '',
    depends=>[],
    duplicateLOC=>0,
    entid => $ent->id(),
    group => '',
    id => $id,
    indirect => [],
    LOC=> '',
    longname => $ent->longname(1),
    maxCBO => $dependCount,
    maxRFC => $funcCalls,
    maxWMC => $declFuncs,
    maxWMCM=> $maxCyclo,
    name => $ent->name(),
    relname => $ent->relname(),
    usefulCommentToCode => '',
    vfi => 0,
    vfo => 0,
    violations => {},
    ULOC=> '',
  };
   bless($self, $class);
   return($self);
}

sub vfiInc {
    my $self = shift;
    $self->{vfi} = $self->{vfi}+1;
}

sub vfoInc {
    my $self = shift;
    $self->{vfo} = $self->{vfo}+1;
}

1;


package Match;
sub new{
  my ($class,$text, $numLines) = @_;
  my $self = bless { 
    _fileList => [],
    _lineList => [],
    _lexList => [],
    locCount => 0,
    text => $text,
    numLines => $numLines,
    }, $class;
  return $self;
}

sub addLoc{
  my ($self, $fileEnt, $line) = @_;
  push @{$self->{_fileList}},$fileEnt;
  push @{$self->{_lineList}}, $line;
  $self->{locCount}++;
}

sub addLex{
  my ($self, $i, $lexeme) = @_;
  ${$self->{_lexList}}[$i]= $lexeme;
}

sub update{
  my ($self, $text, $numLines) = @_;
  $self->{text} = $text if $text;
  $self->{numLines} = $numLines if $numLines;
}

sub getLoc{
  my ($self, $i) = @_;
  return if  $i >= $self->{locCount};
  return (@{$self->{_fileList}}[$i],@{$self->{_lineList}}[$i]);
}

sub getLex{
  my ($self, $i) = @_;
  return if  $i >= $self->{locCount};
  my $lex =  @{$self->{_lexList}}[$i];
  return $lex;
}

sub getLocCount{
  my ($self) = @_;
  return $self->{locCount};
}

sub getText{
  my ($self) = @_;
  return $self->{text};
}

sub getNumLines{
  my ($self) = @_;
  return $self->{numLines};
}

sub removeLocation{
  my ($self,$victim) = @_;
  return unless $victim;
  splice @{$self->{_fileList}}, $victim,1;
  splice @{$self->{_lineList}}, $victim,1;
  $self->{locCount}--;
}

sub removeDuplicateLocations{
  my ($self,$hash, $i) = @_;
  my %dupList = %{$hash};
  my @victims;
  if (!$i){
    for (my $j=$self->{locCount}-1; $j >=0 ;$j--){
      push @victims,$j if $dupList{@{$self->{_fileList}}[$j]->id}{@{$self->{_lineList}}[$j]};
    }
  }else{
    push @victims,$i if $dupList{@{$self->{_fileList}}[$i]->id}{@{$self->{_lineList}}[$i]};
  }
  foreach my $j(@victims){
    splice @{$self->{_fileList}}, $j,1;
    splice @{$self->{_lineList}}, $j,1;
    $self->{locCount}--;
  }
  return scalar(@victims) if @victims;
}

sub updateFileMetrics{
  my ($self) = @_;
  for (my $i;$i<$self->{locCount};$i++){
    my $fileObj = $fileObjsByEntID{$self->{_fileList}[$i]->id};
    $fileObj->{duplicateLOC}+= $self->{numLines};
  }
}

sub printMatch{
  my ($self) = @_;
  my $string = $self->{numLines}." useful lines duplicated in ".$self->{locCount}." locations\n";
  for (my $i;$i<$self->{locCount};$i++){
    $string .="  ".@{$self->{_fileList}}[$i]->relname. "(". @{$self->{_lineList}}[$i].")\n";
  }
  return $string;
}

1;
