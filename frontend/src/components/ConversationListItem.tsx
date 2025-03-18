import React from 'react';

interface ConversationListItemProps {
  conversation: { id: string; title: string };
  isSelected: boolean;
  onSelect: (id: string) => void;
}

const ConversationListItem: React.FC<ConversationListItemProps> = ({
  conversation,
  isSelected,
  onSelect,
}) => {
  return (
    <div
      className={`py-2 px-4 hover:bg-gray-200 dark:hover:bg-gray-700 cursor-pointer rounded-md ${
        isSelected ? 'bg-gray-300 dark:bg-gray-600' : ''
      }`}
      onClick={() => onSelect(conversation.id)}
    >
      {conversation.title}
    </div>
  );
};

export default ConversationListItem;
