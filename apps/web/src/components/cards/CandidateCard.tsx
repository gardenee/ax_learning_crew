import { useMemo, useState } from 'react';
import type { RecommendationCardBlock } from '@/lib/types/blocks';
import {
  IconClock,
  IconPin,
  IconThumbsDown,
  IconThumbsUp,
  IconWalk,
  IconWon,
} from '@/components/shell/icons';
import { submitFeedback } from '@/lib/api/feedback';
import { useToast } from '@/components/shell/Toast';

type CandidateCardProps = RecommendationCardBlock & { sessionId?: string | null };

const FALLBACK_DISLIKE_CHIPS = [
  '너무 비쌈',
  '너무 멈',
  '웨이팅이 김',
  '오늘 안땡김',
  '최근에 가봄',
];

export function CandidateCard({
  rank,
  restaurant,
  reason,
  evidence,
  dislike_reason_chips,
  sessionId,
}: CandidateCardProps) {
  const isTop = rank === 1;

  const toast = useToast();

  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [visited, setVisited] = useState(false);
  const [sending, setSending] = useState(false);

  const [dislikeOpen, setDislikeOpen] = useState(false);
  const [pickedReasons, setPickedReasons] = useState<string[]>([]);
  const [freeText, setFreeText] = useState('');

  const reasonChips = useMemo(
    () => (dislike_reason_chips && dislike_reason_chips.length > 0
      ? dislike_reason_chips
      : FALLBACK_DISLIKE_CHIPS),
    [dislike_reason_chips],
  );

  const commonArgs = {
    sessionId: sessionId ?? null,
    restaurantId: restaurant.id,
    restaurantName: restaurant.name,
  };

  const send = async (payload: Parameters<typeof submitFeedback>[0]) => {
    setSending(true);
    try {
      await submitFeedback(payload);
    } catch (err) {
      console.error('feedback error', err);
    } finally {
      setSending(false);
    }
  };

  const onLike = async () => {
    if (sending) return;
    if (liked) {
      setLiked(false);
      await send({ ...commonArgs, verdict: 'liked', clear: true });
      toast.show('좋아요를 취소했어요');
      return;
    }
    setLiked(true);
    setDisliked(false);
    setDislikeOpen(false);
    setPickedReasons([]);
    setFreeText('');
    await send({ ...commonArgs, verdict: 'liked' });
    toast.show('좋아하는 곳으로 기억할게요');
  };

  const onDislikeButton = async () => {
    if (sending) return;
    if (disliked) {
      setDisliked(false);
      setDislikeOpen(false);
      await send({ ...commonArgs, verdict: 'disliked', clear: true });
      toast.show('별로예요를 취소했어요');
      return;
    }
    setDislikeOpen((v) => !v);
  };

  const toggleReason = (chip: string) => {
    setPickedReasons((prev) =>
      prev.includes(chip) ? prev.filter((c) => c !== chip) : [...prev, chip],
    );
  };

  const onSubmitDislike = async () => {
    if (sending) return;
    const trimmed = freeText.trim();
    setDisliked(true);
    setLiked(false);
    setDislikeOpen(false);
    await send({
      ...commonArgs,
      verdict: 'disliked',
      reasonTags: pickedReasons,
      freeText: trimmed || null,
    });
    toast.show('다음 추천에 반영할게요');
  };

  const onCancelDislike = () => {
    setDislikeOpen(false);
    setPickedReasons([]);
    setFreeText('');
  };

  const onVisited = async () => {
    if (sending) return;
    const next = !visited;
    setVisited(next);
    await send({
      ...commonArgs,
      verdict: 'visited',
      clear: !next ? true : false,
    });
    toast.show(next ? '다녀온 곳으로 기록했어요' : '방문 기록을 취소했어요');
  };

  return (
    <div className={`rec ${isTop ? 'rec--top' : ''}`}>
      {isTop && (
        <span className="rec__ribbon">오늘의 1픽</span>
      )}
      <div className="rec__head">
        <span className="rec__rank">{rank}</span>
        <h3 className="rec__name">{restaurant.name}</h3>
        {(() => {
          const url = restaurant.map_url
            || (restaurant.name ? `https://map.kakao.com/?q=${encodeURIComponent(restaurant.name)}` : null);
          return url ? (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="rec__map-link"
              title="지도에서 보기"
              aria-label="지도에서 보기"
            >
              🗺️
            </a>
          ) : null;
        })()}
        <span className="rec__cat">{restaurant.category}</span>
      </div>

      <div className="rec__meta">
        {(typeof restaurant.walk_minutes === 'number' || typeof restaurant.distance_m === 'number') && (
          <span>
            <IconWalk />
            {typeof restaurant.walk_minutes === 'number' && `도보 ${restaurant.walk_minutes}분`}
            {typeof restaurant.walk_minutes === 'number' && typeof restaurant.distance_m === 'number' && ' · '}
            {typeof restaurant.distance_m === 'number' && `${restaurant.distance_m}m`}
          </span>
        )}
        {restaurant.budget_label && (
          <span>
            <IconWon />
            {restaurant.budget_label}
          </span>
        )}
        {restaurant.estimated_meal_minutes != null && (
          <span>
            <IconClock />
            식사 약 {restaurant.estimated_meal_minutes}분
          </span>
        )}
      </div>

      <p className="rec__reason">{reason}</p>

      {(() => {
        const items = evidence.filter((e) => e.label?.trim() || e.text?.trim());
        if (items.length === 0) return null;
        return (
          <ul className="rec__evidence">
            {items.map((e, i) => (
              <li key={i}>
                <strong>{e.label}</strong>
                <span>{e.text}</span>
              </li>
            ))}
          </ul>
        );
      })()}

      <div className="rec__feedback" role="group" aria-label="피드백">
        <div className="rec__feedback-left">
          <button
            type="button"
            className={`fb fb--like ${liked ? 'is-active' : ''}`}
            onClick={onLike}
            disabled={sending}
            aria-pressed={liked}
          >
            <IconThumbsUp /> 좋아요
          </button>
          <button
            type="button"
            className={`fb fb--dislike ${disliked ? 'is-active' : ''} ${dislikeOpen ? 'is-open' : ''}`}
            onClick={onDislikeButton}
            disabled={sending}
            aria-pressed={disliked}
            aria-expanded={dislikeOpen}
          >
            <IconThumbsDown /> 별로예요
          </button>
        </div>
        <button
          type="button"
          className={`fb fb--visited ${visited ? 'is-active' : ''}`}
          onClick={onVisited}
          disabled={sending}
          aria-pressed={visited}
        >
          <IconPin /> 오늘은 여기!
        </button>
      </div>

      {dislikeOpen && (
        <div className="rec__dislike-form" role="region" aria-label="별로였던 이유">
          <p className="rec__dislike-prompt">왜 별로였나요? (선택)</p>
          <div className="rec__dislike-chips">
            {reasonChips.map((chip) => {
              const active = pickedReasons.includes(chip);
              return (
                <button
                  key={chip}
                  type="button"
                  className={`chip ${active ? 'chip--on' : ''}`}
                  onClick={() => toggleReason(chip)}
                >
                  {chip}
                </button>
              );
            })}
          </div>
          <input
            type="text"
            className="rec__dislike-input"
            placeholder="다른 이유가 있다면 적어주세요"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            maxLength={200}
          />
          <div className="rec__dislike-actions">
            <button
              type="button"
              className="fb fb--ghost"
              onClick={onCancelDislike}
              disabled={sending}
            >
              취소
            </button>
            <button
              type="button"
              className="fb fb--primary"
              onClick={onSubmitDislike}
              disabled={sending}
            >
              저장
            </button>
          </div>
          <p className="rec__dislike-hint">
            이유를 남기면 이 식당이 자동 제외되지 않고, 선호로 녹아들어요.
          </p>
        </div>
      )}
    </div>
  );
}
