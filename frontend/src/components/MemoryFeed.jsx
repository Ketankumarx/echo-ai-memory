import { useState, useMemo } from 'react';
import { MemoryCard } from './MemoryCard';
import { SparklesIcon, SearchIcon, BrainIcon } from './Icons';

export const MemoryFeed = ({ memories, isLoading, onDeleteMemory }) => {
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const categories = [
    { id: 'all', label: 'All Memories' },
    { id: 'deadline', label: 'Deadlines' },
    { id: 'suggestion', label: 'Suggestions' },
    { id: 'work', label: 'Work' },
    { id: 'personal', label: 'Personal' }
  ];

  const filteredMemories = useMemo(() => {
    return memories.filter(item => {
      const cat = (item.category || 'general').toLowerCase();
      const matchesCategory = activeCategory === 'all' || cat === activeCategory;

      if (!matchesCategory) return false;
      if (!searchTerm) return true;

      const s = searchTerm.toLowerCase();
      const fact = (item.fact || item.full_fact || '').toLowerCase();
      const person = (item.person || item.subject || '').toLowerCase();
      const topic = (item.topic || item.object || '').toLowerCase();
      const tags = (item.tags || []).map(t => t.toLowerCase());

      return fact.includes(s) ||
             person.includes(s) ||
             topic.includes(s) ||
             tags.some(t => t.includes(s));
    });
  }, [memories, activeCategory, searchTerm]);

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <BrainIcon size={20} />
          <span>Extracted Memories</span>
        </h2>
        <span className="stats-pill" style={{ fontSize: '0.75rem' }}>
          {filteredMemories.length} / {memories.length}
        </span>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="category-chips">
          {categories.map(cat => (
            <button
              key={cat.id}
              className={`chip-btn ${activeCategory === cat.id ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="search-input-wrapper">
          <SearchIcon size={14} />
          <input
            id="input-search-memories"
            type="text"
            className="search-input"
            placeholder="Search memories (e.g. 'Rahul', 'hackathon', 'Friday', 'React')..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Memory List or Empty State */}
      <div className="memory-list">
        {isLoading ? (
          <div className="empty-state">
            <div className="empty-icon" style={{ animation: 'pulse 1.5s infinite' }}>
              <BrainIcon size={24} />
            </div>
            <div className="empty-title">Loading Knowledge Stream...</div>
            <div className="empty-desc">Connecting to ECHO memory database.</div>
          </div>
        ) : filteredMemories.length > 0 ? (
          filteredMemories.map(mem => (
            <MemoryCard
              key={mem.id}
              memory={mem}
              onDelete={onDeleteMemory}
            />
          ))
        ) : (
          <div className="empty-state">
            <div className="empty-icon">
              <SparklesIcon size={24} />
            </div>
            <div className="empty-title">No Memories Found</div>
            <div className="empty-desc">
              {searchTerm
                ? "No memories matched your search query. Try another keyword or clear the search."
                : "No memories captured yet. Start recording a conversation or enter a note to build your knowledge stream."}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
