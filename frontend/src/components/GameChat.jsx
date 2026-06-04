import React from 'react';
import ChatPanel from './ChatPanel';

export default function GameChat({
  messages,
  onSend,
  disabled,
  chatHidden,
  onToggleHidden,
  roomId,
}) {
  return (
    <ChatPanel
      messages={messages}
      onSend={onSend}
      disabled={disabled}
      maxLength={200}
      showToggle
      chatHidden={chatHidden}
      onToggleHidden={onToggleHidden}
      roomId={roomId}
    />
  );
}
