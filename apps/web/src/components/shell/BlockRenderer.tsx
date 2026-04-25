import type { Block, QuickAction } from '@/lib/types/blocks';
import { AssistantMessage } from '../message/AssistantMessage';
import { ToolStatus } from '../message/ToolStatus';
import { ReasoningBlock } from '../message/ReasoningBlock';
import { CandidateCard } from '../cards/CandidateCard';
import { CompareTable } from '../compare/CompareTable';
import { QuickActionChips } from '../context/QuickActionChips';
import { ChoiceChipsBlockView } from '../context/ChoiceChipsBlock';
import { ContextSummaryPanel } from '../context/ContextSummaryPanel';
import { AlertCard } from '../context/AlertCard';
import { Divider } from '../context/Divider';
import { BadgeRow } from '../context/BadgeRow';
import { MapPin } from '../context/MapPin';
import { LinkCard } from '../context/LinkCard';
import { TextInput } from '../inputs/TextInput';
import { NumberInput } from '../inputs/NumberInput';
import { ChipsInput } from '../inputs/ChipsInput';
import { SelectInput } from '../inputs/SelectInput';
import { SubmitButton } from '../inputs/SubmitButton';

// 단일 block 을 type 에 따라 dispatch.
// 새 block 타입이 생기면 이 switch 한 군데에 case 를 추가하면 된다.
// 폼 관련 input block 은 반드시 FormsProvider 안에서 렌더되어야 한다.
type Props = {
  block: Block;
  onQuickAction?: (action: QuickAction) => void;
  sessionId?: string | null;
  // 과거 대화 복원 턴인지 — true 면 클릭 가능한 block 을 disabled 로 렌더한다.
  readonly?: boolean;
};

export function BlockRenderer({ block, onQuickAction, sessionId, readonly }: Props) {
  switch (block.type) {
    case 'message':
      return <AssistantMessage {...block} />;
    case 'tool_status':
      return <ToolStatus {...block} />;
    case 'reasoning':
      return <ReasoningBlock {...block} />;
    case 'recommendation_card':
      return <CandidateCard {...block} sessionId={sessionId} />;
    case 'comparison_table':
      return <CompareTable {...block} />;
    case 'quick_actions':
      return (
        <QuickActionChips
          {...block}
          onAction={onQuickAction ?? (() => {})}
          disabled={readonly}
        />
      );
    case 'choice_chips':
      return (
        <ChoiceChipsBlockView
          {...block}
          onAction={onQuickAction ?? (() => {})}
          disabled={readonly}
        />
      );
    case 'context_summary':
      return <ContextSummaryPanel {...block} />;
    case 'alert_card':
      return <AlertCard {...block} />;
    case 'divider':
      return <Divider {...block} />;
    case 'badge_row':
      return <BadgeRow {...block} />;
    case 'map_pin':
      return <MapPin {...block} />;
    case 'link_card':
      return <LinkCard {...block} />;
    case 'text_input':
      return <TextInput {...block} />;
    case 'number_input':
      return <NumberInput {...block} />;
    case 'chips_input':
      return <ChipsInput {...block} />;
    case 'select_input':
      return <SelectInput {...block} />;
    case 'submit_button':
      return <SubmitButton {...block} />;
    default:
      return null;
  }
}
