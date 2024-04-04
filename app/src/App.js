import React, { useState } from 'react';
import { Box } from '@mui/material';
import './Chatpage.css';
import Header from "./components/Header";
import ChatInput from "./components/ChatInput";
import ChatMessage from "./components/ChatMessage";
import ChatStatusIndicator from "./components/ChatStatusIndicator";
import Loading from "./components/Loading";
import { useThread } from './hooks/useThread';
import { useRunPolling } from './hooks/useRunPolling';
import { useRunRequiredActionsProcessing } from './hooks/useRunRequiredActionsProcessing';
import { useRunStatus } from './hooks/useRunStatus';
import { postMessage } from "./services/api";

function App() {
    const [run, setRun] = useState(undefined);
    const { threadId, messages, addMessageOptimistically, clearThread } = useThread(run, setRun);
    useRunPolling(threadId, run, setRun);
    useRunRequiredActionsProcessing(run, setRun);
    const { status, processing } = useRunStatus(run);

    const handleSendMessage = (messageContent) => {
        addMessageOptimistically(messageContent);

        postMessage(threadId, messageContent)
            .then(response => {
                setRun(response);
            })
            .catch(error => {
                console.error("Failed to send message:", error);
            });
    };

    let messageList = messages
        .slice().reverse()
        .filter((message) => !message.hidden)
        .map((message) => (
            <ChatMessage
                message={message.content}
                role={message.role}
                key={message.id}
                sx={{ color: '#333' }} // Set the text color to a darker shade
            />
        ));

    return (
        <Box
          className="md:container md:mx-auto lg:px-32 h-screen flex flex-col"
          sx={{
            bgcolor: 'white',
            overflow: 'auto',
          }}
        >
            <Header onNewChat={clearThread} />
            <Box className="flex flex-col-reverse grow overflow-scroll">
                {status !== undefined && <ChatStatusIndicator status={status} />}
                {processing && <Loading />}
                {messageList}
            </Box>
            <Box className="my-4">
                <ChatInput
                    onSend={handleSendMessage}
                    disabled={processing}
                />
            </Box>
        </Box>
    );
}

export default App;
