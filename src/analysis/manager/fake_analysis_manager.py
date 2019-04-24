import datetime
import random

from django.utils import timezone
from django.utils.timezone import now

from analysis.manager.analysis_manager import AnalysisManager
from analysis.tree_helper import make_tree_map, empty_tree
from store.models import Measurement, Repository
from cbri.reporting import logger


class FakeAnalysisManager(AnalysisManager):
    """Makes fake measurement data!"""

    def __init__(self, repo: Repository, num_weeks: int):
        self.repo = repo
        self.num_weeks = num_weeks

    def make_measurement(self) -> Measurement:
        return self._make_fake_measurement(get_current_time())

    def make_history(self) -> list:
        """Make fake measurements for the number of weeks we've been told to make!"""
        history = []
        current_time = get_current_time()

        # Older to newer
        for i in reversed(range(self.num_weeks)):
            measurement_time = current_time - datetime.timedelta(days=7 * i)
            history.append(self._make_fake_measurement(measurement_time))

        return history

    def make_zero_measurement(self) -> Measurement:
        """ Make a zero measurement"""

        # MeasurementViewSet depends on UNDEFINED
        fake_dict = {'date': get_current_time(),
                     'Architecture Type': 'UNDEFINED',
                     'core': False,
                     'Propagation Cost': 0,
                     'Useful Lines of Code (ULOC)': 0,
                     'Classes': 0,
                     'Files': 0,
                     'num_files_in_core': 0,
                     'Core Size': 0,
                     'Overly Complex Files': 0,
                     'percent_files_overly_complex': 0,
                     'useful_lines_of_comments': 0,
                     'Useful Comment Density': 0,
                     'duplicate_uloc': 0,
                     'percent_duplicate_uloc': 0,
                     'revision_id': '',
                     'Components': make_tree_map(empty_tree)
                     }
        return Measurement.create_from_dict(self.repo, fake_dict)

    def _make_fake_measurement(self, date: timezone) -> Measurement:
        """Make a fake measurement at the given time."""

        logger.info("  Making fake measurement for %s" % date)

        # Numbers are +/- 10% of values for SB
        num_files = random.randint(300, 360)
        num_files_in_core = random.randint(135, 165)
        uloc = random.randint(27000, 33000)
        useful_comments = random.randint(6500, 8000)
        duplicate_uloc = random.randint(3400, 4200)
        num_complex = random.randint(20, 26)

        fake_dict = {'date': date,
                     'Architecture Type': 'Random',
                     'core': False,
                     'Propagation Cost': "%.1f" % random.uniform(35, 55),
                     'Useful Lines of Code (ULOC)': uloc,
                     'Classes': random.randint(450, 550),
                     'Files': num_files,
                     'num_files_in_core': num_files_in_core,
                     'Core Size': "%.1f" % (100 * num_files_in_core / num_files),
                     'Overly Complex Files': num_complex,
                     'percent_files_overly_complex': "%.1f" % (100 * num_complex / num_files),
                     'useful_lines_of_comments': useful_comments,
                     'Useful Comment Density': "%.1f" % (100 * useful_comments / uloc),
                     'duplicate_uloc': duplicate_uloc,
                     'percent_duplicate_uloc': "%.1f" % (100 * duplicate_uloc / uloc),
                     'revision_id': 'no revision id',
                     'Components': make_tree_map(fake_tree)
                     }

        return Measurement.create_from_dict(self.repo, fake_dict)


def get_current_time() -> timezone:
    return now().replace(microsecond=0)


# SB output cleaned up
fake_tree = """Project,null,0,0,Project
Peripheral,Project,0,0,Peripheral
Shared,Project,0,0,Shared
Core,Project,0,0,Core
Control,Project,0,0,Control
Isolate,Project,0,0,Isolate
Central,Project,0,0,Central
ChoicePoint.java,Shared,158,0,src/com/stottlerhenke/dynamicscripting/ChoicePoint.java
ChoicePointTable.java,Shared,72,1,src/com/stottlerhenke/dynamicscripting/ChoicePointTable.java
DsAction.java,Shared,37,0,src/com/stottlerhenke/dynamicscripting/DsAction.java
DsSelection.java,Shared,32,0,src/com/stottlerhenke/dynamicscripting/DsSelection.java
DynamicScriptingWrapper.java,Shared,67,3,src/com/stottlerhenke/dynamicscripting/DynamicScriptingWrapper.java
I_DynamicScriptingAdjustor.java,Peripheral,4,0,src/com/stottlerhenke/dynamicscripting/I_DynamicScriptingAdjustor.java
WeightAdjust.java,Shared,136,0,src/com/stottlerhenke/dynamicscripting/WeightAdjust.java
SB_Config.java,Shared,30,0,src/com/stottlerhenke/simbionic/api/SB_Config.java
SB_Engine.java,Control,293,4,src/com/stottlerhenke/simbionic/api/SB_Engine.java
SB_Error.java,Peripheral,17,0,src/com/stottlerhenke/simbionic/api/SB_Error.java
SB_Exception.java,Shared,14,1,src/com/stottlerhenke/simbionic/api/SB_Exception.java
SB_Param.java,Core,360,4,src/com/stottlerhenke/simbionic/api/SB_Param.java
SB_ParamType.java,Shared,6,0,src/com/stottlerhenke/simbionic/api/SB_ParamType.java
EErrCode.java,Shared,6,0,src/com/stottlerhenke/simbionic/common/EErrCode.java
EIdType.java,Shared,7,0,src/com/stottlerhenke/simbionic/common/EIdType.java
Enum.java,Shared,6,0,src/com/stottlerhenke/simbionic/common/Enum.java
GetVersion.java,Peripheral,4,0,src/com/stottlerhenke/simbionic/common/GetVersion.java
SB_FileException.java,Shared,7,1,src/com/stottlerhenke/simbionic/common/SB_FileException.java
SB_ID.java,Shared,21,0,src/com/stottlerhenke/simbionic/common/SB_ID.java
SB_Logger.java,Shared,77,1,src/com/stottlerhenke/simbionic/common/SB_Logger.java
SB_Tokenizer.java,Isolate,58,0,src/com/stottlerhenke/simbionic/common/SB_Tokenizer.java
SB_Util.java,Shared,9,0,src/com/stottlerhenke/simbionic/common/SB_Util.java
SIM_Constants.java,Shared,3,0,src/com/stottlerhenke/simbionic/common/SIM_Constants.java
Table.java,Shared,315,5,src/com/stottlerhenke/simbionic/common/Table.java
Version.java,Shared,18,0,src/com/stottlerhenke/simbionic/common/Version.java
SB_ClassDescription.java,Core,133,3,src/com/stottlerhenke/simbionic/common/classes/SB_ClassDescription.java
SB_ClassMap.java,Core,52,1,src/com/stottlerhenke/simbionic/common/classes/SB_ClassMap.java
SB_ClassMethod.java,Core,108,1,src/com/stottlerhenke/simbionic/common/classes/SB_ClassMethod.java
SB_ClassUtil.java,Shared,18,0,src/com/stottlerhenke/simbionic/common/classes/SB_ClassUtil.java
SB_NoSuchMethodException.java,Shared,7,1,src/com/stottlerhenke/simbionic/common/classes/SB_NoSuchMethodException.java
DMFieldMap.java,Core,39,0,src/com/stottlerhenke/simbionic/common/debug/DMFieldMap.java
MFCSocketInputStream.java,Shared,31,1,src/com/stottlerhenke/simbionic/common/debug/MFCSocketInputStream.java
MFCSocketOutputStream.java,Shared,35,1,src/com/stottlerhenke/simbionic/common/debug/MFCSocketOutputStream.java
MessageTypeAssoc.java,Shared,6,0,src/com/stottlerhenke/simbionic/common/debug/MessageTypeAssoc.java
SB_DebugMessage.java,Core,439,4,src/com/stottlerhenke/simbionic/common/debug/SB_DebugMessage.java
SB_ExpressionNode.java,Shared,3,0,src/com/stottlerhenke/simbionic/common/parser/SB_ExpressionNode.java
DocHandler.java,Shared,8,0,src/com/stottlerhenke/simbionic/common/xmlConverters/DocHandler.java
QDParser.java,Shared,245,2,src/com/stottlerhenke/simbionic/common/xmlConverters/QDParser.java
XMLObjectConverter.java,Core,99,3,src/com/stottlerhenke/simbionic/common/xmlConverters/XMLObjectConverter.java
XMLObjectConverterImplementation.java,Core,118,2,src/com/stottlerhenke/simbionic/common/xmlConverters/XMLObjectConverterImplementation.java
XMLObjectConverterInterface.java,Core,15,0,src/com/stottlerhenke/simbionic/common/xmlConverters/XMLObjectConverterInterface.java
Action.java,Shared,12,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Action.java
ActionFolder.java,Shared,14,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/ActionFolder.java
ActionFolderGroup.java,Shared,28,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/ActionFolderGroup.java
ActionNode.java,Shared,46,1,src/com/stottlerhenke/simbionic/common/xmlConverters/model/ActionNode.java
Behavior.java,Core,43,2,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Behavior.java
BehaviorFolder.java,Core,14,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/BehaviorFolder.java
BehaviorFolderGroup.java,Core,26,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/BehaviorFolderGroup.java
Binding.java,Shared,27,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Binding.java
Category.java,Shared,10,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Category.java
CompoundActionNode.java,Shared,13,1,src/com/stottlerhenke/simbionic/common/xmlConverters/model/CompoundActionNode.java
Condition.java,Shared,20,1,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Condition.java
Connector.java,Core,99,2,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Connector.java
Constant.java,Shared,14,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Constant.java
Descriptor.java,Shared,31,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Descriptor.java
Folder.java,Shared,7,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Folder.java
Function.java,Shared,32,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Function.java
Global.java,Shared,20,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Global.java
JavaScript.java,Shared,29,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/JavaScript.java
Local.java,Shared,11,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Local.java
Node.java,Shared,60,2,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Node.java
NodeGroup.java,Shared,43,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/NodeGroup.java
Parameter.java,Shared,25,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Parameter.java
Poly.java,Core,76,2,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Poly.java
Predicate.java,Shared,21,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Predicate.java
PredicateFolder.java,Shared,14,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/PredicateFolder.java
PredicateFolderGroup.java,Shared,28,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/PredicateFolderGroup.java
SimBionicJava.java,Core,95,3,src/com/stottlerhenke/simbionic/common/xmlConverters/model/SimBionicJava.java
Start.java,Core,37,0,src/com/stottlerhenke/simbionic/common/xmlConverters/model/Start.java
Parser.java,Shared,29,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/Parser.java
StackParser.java,Shared,25,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/StackParser.java
BooleanParser.java,Shared,16,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/basicParsers/BooleanParser.java
IntegerParser.java,Shared,16,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/basicParsers/IntegerParser.java
StringParser.java,Shared,16,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/basicParsers/StringParser.java
ActionFolderGroupSAXReader.java,Shared,43,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ActionFolderGroupSAXReader.java
ActionFolderSAXReader.java,Shared,51,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ActionFolderSAXReader.java
ActionGroupSAXReader.java,Peripheral,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ActionGroupSAXReader.java
ActionNodeGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ActionNodeGroupSAXReader.java
ActionNodeSAXReader.java,Shared,122,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ActionNodeSAXReader.java
ActionSAXReader.java,Shared,66,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ActionSAXReader.java
BehaviorFolderGroupSAXReader.java,Core,43,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/BehaviorFolderGroupSAXReader.java
BehaviorFolderSAXReader.java,Core,51,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/BehaviorFolderSAXReader.java
BehaviorSAXReader.java,Core,85,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/BehaviorSAXReader.java
BindingGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/BindingGroupSAXReader.java
BindingSAXReader.java,Shared,49,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/BindingSAXReader.java
CategoryGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/CategoryGroupSAXReader.java
CategorySAXReader.java,Shared,58,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/CategorySAXReader.java
CompoundActionNodeGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/CompoundActionNodeGroupSAXReader.java
CompoundActionNodeSAXReader.java,Shared,90,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/CompoundActionNodeSAXReader.java
ConditionGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ConditionGroupSAXReader.java
ConditionSAXReader.java,Shared,90,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ConditionSAXReader.java
ConnectorGroupSAXReader.java,Core,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ConnectorGroupSAXReader.java
ConnectorSAXReader.java,Core,130,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ConnectorSAXReader.java
ConstantGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ConstantGroupSAXReader.java
ConstantSAXReader.java,Shared,57,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ConstantSAXReader.java
DescriptorGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/DescriptorGroupSAXReader.java
DescriptorSAXReader.java,Shared,58,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/DescriptorSAXReader.java
GlobalGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/GlobalGroupSAXReader.java
GlobalSAXReader.java,Shared,65,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/GlobalSAXReader.java
ImportedJavaClassGroupSAXReader.java,Shared,36,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ImportedJavaClassGroupSAXReader.java
IndexGroupSAXReader.java,Shared,36,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/IndexGroupSAXReader.java
JavaScriptSAXReader.java,Shared,51,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/JavaScriptSAXReader.java
JsFileGroupSAXReader.java,Shared,36,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/JsFileGroupSAXReader.java
LocalGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/LocalGroupSAXReader.java
LocalSAXReader.java,Shared,49,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/LocalSAXReader.java
NodeGroupSAXReader.java,Shared,60,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/NodeGroupSAXReader.java
ParameterGroupSAXReader.java,Shared,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ParameterGroupSAXReader.java
ParameterSAXReader.java,Shared,49,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/ParameterSAXReader.java
PolyGroupSAXReader.java,Core,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/PolyGroupSAXReader.java
PolySAXReader.java,Core,78,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/PolySAXReader.java
PredicateFolderGroupSAXReader.java,Shared,43,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/PredicateFolderGroupSAXReader.java
PredicateFolderSAXReader.java,Shared,51,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/PredicateFolderSAXReader.java
PredicateGroupSAXReader.java,Peripheral,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/PredicateGroupSAXReader.java
PredicateSAXReader.java,Shared,74,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/PredicateSAXReader.java
SimBionicJavaSAXReader.java,Core,131,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/SimBionicJavaSAXReader.java
StartConnectorGroupSAXReader.java,Core,36,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/StartConnectorGroupSAXReader.java
StartSAXReader.java,Core,58,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/readers/StartSAXReader.java
ActionFolderGroupSAXWriter.java,Core,25,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ActionFolderGroupSAXWriter.java
ActionFolderSAXWriter.java,Core,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ActionFolderSAXWriter.java
ActionGroupSAXWriter.java,Peripheral,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ActionGroupSAXWriter.java
ActionNodeGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ActionNodeGroupSAXWriter.java
ActionNodeSAXWriter.java,Shared,28,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ActionNodeSAXWriter.java
ActionSAXWriter.java,Shared,21,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ActionSAXWriter.java
BehaviorFolderGroupSAXWriter.java,Core,26,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/BehaviorFolderGroupSAXWriter.java
BehaviorFolderSAXWriter.java,Core,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/BehaviorFolderSAXWriter.java
BehaviorSAXWriter.java,Core,27,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/BehaviorSAXWriter.java
BindingGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/BindingGroupSAXWriter.java
BindingSAXWriter.java,Shared,15,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/BindingSAXWriter.java
CategoryGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/CategoryGroupSAXWriter.java
CategorySAXWriter.java,Shared,20,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/CategorySAXWriter.java
CompoundActionNodeGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/CompoundActionNodeGroupSAXWriter.java
CompoundActionNodeSAXWriter.java,Shared,24,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/CompoundActionNodeSAXWriter.java
ConditionGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ConditionGroupSAXWriter.java
ConditionSAXWriter.java,Shared,24,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ConditionSAXWriter.java
ConnectorGroupSAXWriter.java,Core,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ConnectorGroupSAXWriter.java
ConnectorSAXWriter.java,Core,29,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ConnectorSAXWriter.java
ConstantGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ConstantGroupSAXWriter.java
ConstantSAXWriter.java,Shared,16,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ConstantSAXWriter.java
DescriptorGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/DescriptorGroupSAXWriter.java
DescriptorSAXWriter.java,Shared,20,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/DescriptorSAXWriter.java
GlobalGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/GlobalGroupSAXWriter.java
GlobalSAXWriter.java,Shared,17,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/GlobalSAXWriter.java
ImportedJavaClassGroupSAXWriter.java,Shared,17,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ImportedJavaClassGroupSAXWriter.java
IndexGroupSAXWriter.java,Shared,17,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/IndexGroupSAXWriter.java
JavaScriptSAXWriter.java,Shared,23,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/JavaScriptSAXWriter.java
JsFileGroupSAXWriter.java,Shared,17,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/JsFileGroupSAXWriter.java
LocalGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/LocalGroupSAXWriter.java
LocalSAXWriter.java,Shared,15,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/LocalSAXWriter.java
NodeGroupSAXWriter.java,Core,25,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/NodeGroupSAXWriter.java
ParameterGroupSAXWriter.java,Shared,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ParameterGroupSAXWriter.java
ParameterSAXWriter.java,Shared,15,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/ParameterSAXWriter.java
PolyGroupSAXWriter.java,Core,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/PolyGroupSAXWriter.java
PolySAXWriter.java,Core,38,1,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/PolySAXWriter.java
PredicateFolderGroupSAXWriter.java,Core,26,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/PredicateFolderGroupSAXWriter.java
PredicateFolderSAXWriter.java,Core,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/PredicateFolderSAXWriter.java
PredicateGroupSAXWriter.java,Peripheral,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/PredicateGroupSAXWriter.java
PredicateSAXWriter.java,Shared,22,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/PredicateSAXWriter.java
SimBionicJavaSAXWriter.java,Core,52,2,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/SimBionicJavaSAXWriter.java
StartConnectorGroupSAXWriter.java,Core,19,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/StartConnectorGroupSAXWriter.java
StartSAXWriter.java,Core,20,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/StartSAXWriter.java
Utils.java,Shared,57,0,src/com/stottlerhenke/simbionic/common/xmlConverters/sax/writers/Utils.java
ETypeType.java,Shared,7,0,src/com/stottlerhenke/simbionic/editor/ETypeType.java
ETypeValid.java,Shared,10,0,src/com/stottlerhenke/simbionic/editor/ETypeValid.java
FileManager.java,Core,68,1,src/com/stottlerhenke/simbionic/editor/FileManager.java
SB_Action.java,Core,38,2,src/com/stottlerhenke/simbionic/editor/SB_Action.java
SB_Behavior.java,Core,270,4,src/com/stottlerhenke/simbionic/editor/SB_Behavior.java
SB_Binding.java,Core,109,3,src/com/stottlerhenke/simbionic/editor/SB_Binding.java
SB_Breakpoint.java,Core,22,0,src/com/stottlerhenke/simbionic/editor/SB_Breakpoint.java
SB_CancelException.java,Shared,2,1,src/com/stottlerhenke/simbionic/editor/SB_CancelException.java
SB_Class.java,Core,226,4,src/com/stottlerhenke/simbionic/editor/SB_Class.java
SB_ClassMember.java,Core,97,3,src/com/stottlerhenke/simbionic/editor/SB_ClassMember.java
SB_ClassMethod.java(2),Core,151,3,src/com/stottlerhenke/simbionic/editor/SB_ClassMethod.java
SB_ClassMethodParameter.java,Core,84,3,src/com/stottlerhenke/simbionic/editor/SB_ClassMethodParameter.java
SB_Constant.java,Core,57,2,src/com/stottlerhenke/simbionic/editor/SB_Constant.java
SB_Entity.java,Shared,14,0,src/com/stottlerhenke/simbionic/editor/SB_Entity.java
SB_ErrorInfo.java,Shared,3,0,src/com/stottlerhenke/simbionic/editor/SB_ErrorInfo.java
SB_Folder.java,Shared,29,1,src/com/stottlerhenke/simbionic/editor/SB_Folder.java
SB_Frame.java,Core,17,0,src/com/stottlerhenke/simbionic/editor/SB_Frame.java
SB_Function.java,Core,68,3,src/com/stottlerhenke/simbionic/editor/SB_Function.java
SB_Global.java,Core,83,3,src/com/stottlerhenke/simbionic/editor/SB_Global.java
SB_Package.java,Core,148,3,src/com/stottlerhenke/simbionic/editor/SB_Package.java
SB_Parameter.java,Core,26,1,src/com/stottlerhenke/simbionic/editor/SB_Parameter.java
SB_Predicate.java,Core,55,3,src/com/stottlerhenke/simbionic/editor/SB_Predicate.java
SB_TypeChangeListener.java,Core,3,0,src/com/stottlerhenke/simbionic/editor/SB_TypeChangeListener.java
SB_TypeManager.java,Core,245,4,src/com/stottlerhenke/simbionic/editor/SB_TypeManager.java
SB_Variable.java,Core,80,3,src/com/stottlerhenke/simbionic/editor/SB_Variable.java
SimBionicEditor.java,Core,467,4,src/com/stottlerhenke/simbionic/editor/SimBionicEditor.java
SimBionicEditorAPI.java,Control,158,3,src/com/stottlerhenke/simbionic/editor/SimBionicEditorAPI.java
UserObject.java,Shared,118,3,src/com/stottlerhenke/simbionic/editor/UserObject.java
Util.java,Shared,166,3,src/com/stottlerhenke/simbionic/editor/Util.java
SBLogger.java,Peripheral,93,1,src/com/stottlerhenke/simbionic/editor/common/SBLogger.java
AutoCompletionHelper.java,Core,194,3,src/com/stottlerhenke/simbionic/editor/gui/AutoCompletionHelper.java
ComponentRegistry.java,Core,53,2,src/com/stottlerhenke/simbionic/editor/gui/ComponentRegistry.java
EditorTree.java,Core,283,4,src/com/stottlerhenke/simbionic/editor/gui/EditorTree.java
FileChooserAction.java,Core,55,0,src/com/stottlerhenke/simbionic/editor/gui/FileChooserAction.java
ImageBundle.java,Isolate,35,1,src/com/stottlerhenke/simbionic/editor/gui/ImageBundle.java
JavaScriptDialog.java,Core,81,2,src/com/stottlerhenke/simbionic/editor/gui/JavaScriptDialog.java
ModalDialog.java,Core,43,2,src/com/stottlerhenke/simbionic/editor/gui/ModalDialog.java
SB_Autocomplete.java,Core,644,5,src/com/stottlerhenke/simbionic/editor/gui/SB_Autocomplete.java
SB_AutocompleteListener.java,Shared,6,0,src/com/stottlerhenke/simbionic/editor/gui/SB_AutocompleteListener.java
SB_AutocompleteTextArea.java,Core,246,4,src/com/stottlerhenke/simbionic/editor/gui/SB_AutocompleteTextArea.java
SB_BindingsHolder.java,Core,12,0,src/com/stottlerhenke/simbionic/editor/gui/SB_BindingsHolder.java
SB_BindingsTable.java,Core,267,4,src/com/stottlerhenke/simbionic/editor/gui/SB_BindingsTable.java
SB_BreakpointFrame.java,Core,180,2,src/com/stottlerhenke/simbionic/editor/gui/SB_BreakpointFrame.java
SB_Button.java,Shared,14,1,src/com/stottlerhenke/simbionic/editor/gui/SB_Button.java
SB_Canvas.java,Core,791,5,src/com/stottlerhenke/simbionic/editor/gui/SB_Canvas.java
SB_CanvasMomento.java,Core,25,1,src/com/stottlerhenke/simbionic/editor/gui/SB_CanvasMomento.java
SB_Catalog.java,Core,2150,5,src/com/stottlerhenke/simbionic/editor/gui/SB_Catalog.java
SB_Category.java,Core,32,1,src/com/stottlerhenke/simbionic/editor/gui/SB_Category.java
SB_ChangeListener.java,Core,4,0,src/com/stottlerhenke/simbionic/editor/gui/SB_ChangeListener.java
SB_CommentHolder.java,Shared,10,0,src/com/stottlerhenke/simbionic/editor/gui/SB_CommentHolder.java
SB_Condition.java,Core,160,2,src/com/stottlerhenke/simbionic/editor/gui/SB_Condition.java
SB_Connector.java,Core,498,5,src/com/stottlerhenke/simbionic/editor/gui/SB_Connector.java
SB_ConnectorComposite.java,Core,85,2,src/com/stottlerhenke/simbionic/editor/gui/SB_ConnectorComposite.java
SB_Debugger.java,Core,592,4,src/com/stottlerhenke/simbionic/editor/gui/SB_Debugger.java
SB_Descriptor.java,Core,49,2,src/com/stottlerhenke/simbionic/editor/gui/SB_Descriptor.java
SB_Descriptors.java,Core,292,4,src/com/stottlerhenke/simbionic/editor/gui/SB_Descriptors.java
SB_Drawable.java,Shared,65,3,src/com/stottlerhenke/simbionic/editor/gui/SB_Drawable.java
SB_DrawableComposite.java,Shared,198,3,src/com/stottlerhenke/simbionic/editor/gui/SB_DrawableComposite.java
SB_Element.java,Core,388,4,src/com/stottlerhenke/simbionic/editor/gui/SB_Element.java
SB_ElementComposite.java,Core,110,2,src/com/stottlerhenke/simbionic/editor/gui/SB_ElementComposite.java
SB_Line.java,Core,42,0,src/com/stottlerhenke/simbionic/editor/gui/SB_Line.java
SB_LocalsTree.java,Core,285,4,src/com/stottlerhenke/simbionic/editor/gui/SB_LocalsTree.java
SB_MenuBar.java,Core,88,1,src/com/stottlerhenke/simbionic/editor/gui/SB_MenuBar.java
SB_MultiBindingsTable.java,Core,30,1,src/com/stottlerhenke/simbionic/editor/gui/SB_MultiBindingsTable.java
SB_MultiDialog.java,Core,129,3,src/com/stottlerhenke/simbionic/editor/gui/SB_MultiDialog.java
SB_MultiRectangle.java,Core,51,2,src/com/stottlerhenke/simbionic/editor/gui/SB_MultiRectangle.java
SB_Output.java,Core,233,4,src/com/stottlerhenke/simbionic/editor/gui/SB_Output.java
SB_OutputBar.java,Core,56,1,src/com/stottlerhenke/simbionic/editor/gui/SB_OutputBar.java
SB_Polymorphism.java,Core,546,5,src/com/stottlerhenke/simbionic/editor/gui/SB_Polymorphism.java
SB_ProjectBar.java,Core,1023,5,src/com/stottlerhenke/simbionic/editor/gui/SB_ProjectBar.java
SB_Rectangle.java,Core,235,4,src/com/stottlerhenke/simbionic/editor/gui/SB_Rectangle.java
SB_TabbedCanvas.java,Core,1218,5,src/com/stottlerhenke/simbionic/editor/gui/SB_TabbedCanvas.java
SB_ToolBar.java,Core,900,5,src/com/stottlerhenke/simbionic/editor/gui/SB_ToolBar.java
SimBionicDebugger.java,Control,22,1,src/com/stottlerhenke/simbionic/editor/gui/SimBionicDebugger.java
SimBionicFrame.java,Core,134,2,src/com/stottlerhenke/simbionic/editor/gui/SimBionicFrame.java
StandardDialog.java,Shared,81,2,src/com/stottlerhenke/simbionic/editor/gui/StandardDialog.java
TitledComponentPanel.java,Shared,14,1,src/com/stottlerhenke/simbionic/editor/gui/TitledComponentPanel.java
UIUtil.java,Shared,109,1,src/com/stottlerhenke/simbionic/editor/gui/UIUtil.java
DefaultValidator.java,Core,34,1,src/com/stottlerhenke/simbionic/editor/gui/api/DefaultValidator.java
EditorRegistry.java,Core,46,0,src/com/stottlerhenke/simbionic/editor/gui/api/EditorRegistry.java
FindMatcher.java,Shared,4,0,src/com/stottlerhenke/simbionic/editor/gui/api/FindMatcher.java
I_CompileValidator.java,Core,24,1,src/com/stottlerhenke/simbionic/editor/gui/api/I_CompileValidator.java
I_EditorListener.java,Shared,4,0,src/com/stottlerhenke/simbionic/editor/gui/api/I_EditorListener.java
I_ExpressionEditor.java,Shared,4,0,src/com/stottlerhenke/simbionic/editor/gui/api/I_ExpressionEditor.java
AutoCompleteSimbionicProjectDefinitions.java,Core,314,4,src/com/stottlerhenke/simbionic/editor/gui/autocomplete/AutoCompleteSimbionicProjectDefinitions.java
MatchListRenderer.java,Shared,16,1,src/com/stottlerhenke/simbionic/editor/gui/autocomplete/MatchListRenderer.java
SB_GlassPane.java,Shared,109,2,src/com/stottlerhenke/simbionic/editor/gui/autocomplete/SB_GlassPane.java
SB_ErrorNode.java,Shared,20,0,src/com/stottlerhenke/simbionic/editor/parser/SB_ErrorNode.java
SB_ParseNode.java,Shared,7,0,src/com/stottlerhenke/simbionic/editor/parser/SB_ParseNode.java
ActionPredicateAPI.java,Core,171,3,src/com/stottlerhenke/simbionic/engine/ActionPredicateAPI.java
JavaScriptBindings.java,Core,67,2,src/com/stottlerhenke/simbionic/engine/JavaScriptBindings.java
RingListIterator.java,Shared,35,0,src/com/stottlerhenke/simbionic/engine/RingListIterator.java
SB_JavaScriptEngine.java,Core,250,4,src/com/stottlerhenke/simbionic/engine/SB_JavaScriptEngine.java
SB_RingArray.java,Shared,28,1,src/com/stottlerhenke/simbionic/engine/SB_RingArray.java
SB_SimInterface.java,Core,124,3,src/com/stottlerhenke/simbionic/engine/SB_SimInterface.java
SB_SingletonBook.java,Core,54,3,src/com/stottlerhenke/simbionic/engine/SB_SingletonBook.java
SB_Blackboard.java,Core,31,1,src/com/stottlerhenke/simbionic/engine/comm/SB_Blackboard.java
SB_CommCenter.java,Core,77,3,src/com/stottlerhenke/simbionic/engine/comm/SB_CommCenter.java
SB_CommGroup.java,Core,25,0,src/com/stottlerhenke/simbionic/engine/comm/SB_CommGroup.java
SB_CommLink.java,Core,45,2,src/com/stottlerhenke/simbionic/engine/comm/SB_CommLink.java
SB_CommMsg.java,Shared,24,0,src/com/stottlerhenke/simbionic/engine/comm/SB_CommMsg.java
ENodeType.java,Shared,15,0,src/com/stottlerhenke/simbionic/engine/core/ENodeType.java
ESinkType.java,Shared,6,0,src/com/stottlerhenke/simbionic/engine/core/ESinkType.java
ETransitionResult.java,Shared,7,0,src/com/stottlerhenke/simbionic/engine/core/ETransitionResult.java
SB_Action.java(2),Core,12,0,src/com/stottlerhenke/simbionic/engine/core/SB_Action.java
SB_ActionNode.java,Core,111,2,src/com/stottlerhenke/simbionic/engine/core/SB_ActionNode.java
SB_Behavior.java(2),Core,204,4,src/com/stottlerhenke/simbionic/engine/core/SB_Behavior.java
SB_BehaviorClass.java,Core,50,2,src/com/stottlerhenke/simbionic/engine/core/SB_BehaviorClass.java
SB_BehaviorElement.java,Shared,11,0,src/com/stottlerhenke/simbionic/engine/core/SB_BehaviorElement.java
SB_BehaviorNode.java,Core,91,2,src/com/stottlerhenke/simbionic/engine/core/SB_BehaviorNode.java
SB_BehaviorRegistry.java,Core,140,3,src/com/stottlerhenke/simbionic/engine/core/SB_BehaviorRegistry.java
SB_Bindings.java,Core,74,2,src/com/stottlerhenke/simbionic/engine/core/SB_Bindings.java
SB_CompoundNode.java,Core,80,2,src/com/stottlerhenke/simbionic/engine/core/SB_CompoundNode.java
SB_Condition.java(2),Core,69,2,src/com/stottlerhenke/simbionic/engine/core/SB_Condition.java
SB_DelayedAction.java,Core,97,2,src/com/stottlerhenke/simbionic/engine/core/SB_DelayedAction.java
SB_EdgeSink.java,Core,56,2,src/com/stottlerhenke/simbionic/engine/core/SB_EdgeSink.java
SB_Entity.java(2),Core,83,3,src/com/stottlerhenke/simbionic/engine/core/SB_Entity.java
SB_EntityData.java,Core,95,3,src/com/stottlerhenke/simbionic/engine/core/SB_EntityData.java
SB_ExecutionFrame.java,Core,298,4,src/com/stottlerhenke/simbionic/engine/core/SB_ExecutionFrame.java
SB_ExecutionFrameState.java,Core,39,1,src/com/stottlerhenke/simbionic/engine/core/SB_ExecutionFrameState.java
SB_ExecutionStack.java,Core,312,4,src/com/stottlerhenke/simbionic/engine/core/SB_ExecutionStack.java
SB_FinalNode.java,Core,41,2,src/com/stottlerhenke/simbionic/engine/core/SB_FinalNode.java
SB_Function.java(2),Core,12,0,src/com/stottlerhenke/simbionic/engine/core/SB_Function.java
SB_Method.java,Core,11,0,src/com/stottlerhenke/simbionic/engine/core/SB_Method.java
SB_Node.java,Core,89,3,src/com/stottlerhenke/simbionic/engine/core/SB_Node.java
SB_ParamList.java,Core,45,2,src/com/stottlerhenke/simbionic/engine/core/SB_ParamList.java
SB_Parameter.java(2),Shared,12,0,src/com/stottlerhenke/simbionic/engine/core/SB_Parameter.java
SB_TransitionEdge.java,Core,48,2,src/com/stottlerhenke/simbionic/engine/core/SB_TransitionEdge.java
SB_TypeHierarchy.java,Core,55,2,src/com/stottlerhenke/simbionic/engine/core/SB_TypeHierarchy.java
SB_TypeNode.java,Core,55,1,src/com/stottlerhenke/simbionic/engine/core/SB_TypeNode.java
SB_VarBinding.java,Core,78,2,src/com/stottlerhenke/simbionic/engine/core/SB_VarBinding.java
SB_VarClassBinding.java,Control,58,2,src/com/stottlerhenke/simbionic/engine/core/SB_VarClassBinding.java
SB_VariableMap.java,Core,105,3,src/com/stottlerhenke/simbionic/engine/core/SB_VariableMap.java
EEventType.java,Shared,19,0,src/com/stottlerhenke/simbionic/engine/debug/EEventType.java
EStepMode.java,Shared,8,0,src/com/stottlerhenke/simbionic/engine/debug/EStepMode.java
FrameBehavior.java,Shared,7,0,src/com/stottlerhenke/simbionic/engine/debug/FrameBehavior.java
FrameInfo.java,Shared,6,0,src/com/stottlerhenke/simbionic/engine/debug/FrameInfo.java
FrameVarValues.java,Shared,7,0,src/com/stottlerhenke/simbionic/engine/debug/FrameVarValues.java
SB_BreakpointManager.java,Core,125,2,src/com/stottlerhenke/simbionic/engine/debug/SB_BreakpointManager.java
SB_DebugEvent.java,Core,74,2,src/com/stottlerhenke/simbionic/engine/debug/SB_DebugEvent.java
SB_DebugServer.java,Core,127,2,src/com/stottlerhenke/simbionic/engine/debug/SB_DebugServer.java
SB_Debugger.java(2),Core,78,2,src/com/stottlerhenke/simbionic/engine/debug/SB_Debugger.java
SB_EngineQueryInterface.java,Core,140,3,src/com/stottlerhenke/simbionic/engine/debug/SB_EngineQueryInterface.java
SB_EventHandler.java,Core,164,2,src/com/stottlerhenke/simbionic/engine/debug/SB_EventHandler.java
SB_MessageHandler.java,Core,229,3,src/com/stottlerhenke/simbionic/engine/debug/SB_MessageHandler.java
StepModeInfo.java,Shared,9,0,src/com/stottlerhenke/simbionic/engine/debug/StepModeInfo.java
Breakpoint.java,Core,47,0,src/com/stottlerhenke/simbionic/engine/debug/breakpoint/Breakpoint.java
BreakpointBehavior.java,Core,54,2,src/com/stottlerhenke/simbionic/engine/debug/breakpoint/BreakpointBehavior.java
BreakpointElement.java,Core,41,2,src/com/stottlerhenke/simbionic/engine/debug/breakpoint/BreakpointElement.java
BreakpointFunction.java,Core,36,1,src/com/stottlerhenke/simbionic/engine/debug/breakpoint/BreakpointFunction.java
BreakpointGlobalVar.java,Core,28,1,src/com/stottlerhenke/simbionic/engine/debug/breakpoint/BreakpointGlobalVar.java
BreakpointLocalVar.java,Core,33,2,src/com/stottlerhenke/simbionic/engine/debug/breakpoint/BreakpointLocalVar.java
SB_FileRegistry.java,Shared,27,0,src/com/stottlerhenke/simbionic/engine/file/SB_FileRegistry.java
SB_ProjectSpec.java,Control,181,3,src/com/stottlerhenke/simbionic/engine/file/SB_ProjectSpec.java
SB_Specification.java,Control,13,0,src/com/stottlerhenke/simbionic/engine/file/SB_Specification.java
SB_DefaultScheduler.java,Core,165,3,src/com/stottlerhenke/simbionic/engine/manager/SB_DefaultScheduler.java
SB_EntityManager.java,Core,194,3,src/com/stottlerhenke/simbionic/engine/manager/SB_EntityManager.java
SB_EntityRecord.java,Core,65,3,src/com/stottlerhenke/simbionic/engine/manager/SB_EntityRecord.java
SB_IdDispenser.java,Shared,14,0,src/com/stottlerhenke/simbionic/engine/manager/SB_IdDispenser.java
SB_SchedulingAlg.java,Core,14,0,src/com/stottlerhenke/simbionic/engine/manager/SB_SchedulingAlg.java
TickData.java,Core,4,0,src/com/stottlerhenke/simbionic/engine/manager/TickData.java
SB_VarClass.java,Core,97,2,src/com/stottlerhenke/simbionic/engine/parser/SB_VarClass.java
SB_VarInvalid.java,Core,80,2,src/com/stottlerhenke/simbionic/engine/parser/SB_VarInvalid.java
SB_Variable.java(2),Shared,58,2,src/com/stottlerhenke/simbionic/engine/parser/SB_Variable.java
CalendarUtil.java,Shared,83,1,src/com/stottlerhenke/simbionic/util/CalendarUtil.java
MyClass.java,Isolate,43,1,test/com/stottlerhenke/simbionic/test/MyClass.java
MyClassStatic.java,Peripheral,59,1,test/com/stottlerhenke/simbionic/test/MyClassStatic.java
SimBionicJavaReadWriteTest.java,Control,704,4,test/com/stottlerhenke/simbionic/test/SimBionicJavaReadWriteTest.java
DSTest.java,Control,134,2,test/com/stottlerhenke/simbionic/test/dynamicscripting/DSTest.java
DSTestActionType.java,Peripheral,3,0,test/com/stottlerhenke/simbionic/test/dynamicscripting/DSTestActionType.java
DSTestInterface.java,Peripheral,49,0,test/com/stottlerhenke/simbionic/test/dynamicscripting/DSTestInterface.java
TestEngine.java,Control,290,4,test/com/stottlerhenke/simbionic/test/engine/TestEngine.java
TestWrapper.java,Control,133,3,test/com/stottlerhenke/simbionic/test/engine/TestWrapper.java
HelloWorld.java,Control,48,1,test/com/stottlerhenke/simbionic/test/helloworld/HelloWorld.java
LoopTest.java,Control,69,1,test/com/stottlerhenke/simbionic/test/looptest/LoopTest.java
MyEnum.java,Peripheral,3,0,test/com/stottlerhenke/simbionic/test/parameterpassing/MyEnum.java
MyModel.java,Peripheral,15,0,test/com/stottlerhenke/simbionic/test/parameterpassing/MyModel.java
ParameterPassing.java,Control,109,2,test/com/stottlerhenke/simbionic/test/parameterpassing/ParameterPassing.java"""