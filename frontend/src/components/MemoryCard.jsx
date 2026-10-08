import { UserIcon, ClockIcon, TrashIcon } from './Icons';

export const MemoryCard = ({ memory, onDelete }) => {
  const { id } = memory;
  const person = memory.person || memory.subject || (memory.people_mentioned && memory.people_mentioned[0]) || '';
  const category = memory.category || 'general';
  const topic = memory.topic || memory.object || category.toUpperCase();
  const fact = memory.fact || memory.full_fact || '';
  const dateTime = memory.dateTime || 'Recent';
  const tags = memory.tags || [];

  return (
    <div className="memory-card" id={`memory-card-${id}`}>
      <div className="memory-header">
        <div className="memory-meta">
          {person && (
            <span className="badge-person">
              <UserIcon size={12} />
              <span>{person}</span>
            </span>
          )}

          {category && (
            <span className={`badge-category ${category.toLowerCase()}`}>
              <span>{topic}</span>
            </span>
          )}

          <span className="memory-date">
            <ClockIcon size={12} />
            <span>{dateTime}</span>
          </span>
        </div>

        {onDelete && (
          <button
            className="delete-btn"
            onClick={() => onDelete(id)}
            title="Delete this memory"
            aria-label="Delete memory"
          >
            <TrashIcon size={14} />
          </button>
        )}
      </div>

      <div className="memory-fact">
        {fact}
      </div>

      {tags.length > 0 && (
        <div className="memory-tags">
          {tags.map((tag, idx) => (
            <span key={idx} className="tag-item">
              #{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
