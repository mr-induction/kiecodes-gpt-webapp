import { useState, useEffect } from 'react';
import { createNewThread, fetchThread } from "../services/api";
import { runFinishedStates } from "./constants";

export const useThread = (run, setRun) => {
    const [threadId, setThreadId] = useState(undefined);
    const [thread, setThread] = useState({ messages: [] });
    const [actionMessages, setActionMessages] = useState([]);
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        if (!threadId) {
            const localThreadId = localStorage.getItem("thread_id");
            if (localThreadId) {
                setThreadId(localThreadId);
                fetchThread(localThreadId)
                    .then(threadData => {
                        if (threadData && Array.isArray(threadData.messages)) {
                            setThread(threadData);
                        } else {
                            console.error('Invalid thread data', threadData);
                            // Set thread to default value to avoid breaking the app
                            setThread({ messages: [] });
                        }
                    })
                    .catch(error => console.error('Fetch thread error:', error));
            } else {
                createNewThread()
                    .then(data => {
                        if (data && data.thread_id) {
                            setRun(data);
                            setThreadId(data.thread_id);
                            localStorage.setItem("thread_id", data.thread_id);
                        } else {
                            console.error('New thread creation failed');
                        }
                    })
                    .catch(error => console.error('Create thread error:', error));
            }
        }
    }, [threadId, setThreadId, setThread, setRun]);

    useEffect(() => {
        if (run && runFinishedStates.includes(run.status) && run.thread_id) {
            fetchThread(run.thread_id)
                .then(threadData => {
                    if (threadData && Array.isArray(threadData.messages)) {
                        setThread(threadData);
                    } else {
                        console.error('Invalid thread data', threadData);
                        // Set thread to default value to avoid breaking the app
                        setThread({ messages: [] });
                    }
                })
                .catch(error => console.error('Fetch thread error:', error));
        }
    }, [run]);

    useEffect(() => {
        // Ensure thread.messages is always an array before attempting to spread it
        const threadMessages = Array.isArray(thread.messages) ? thread.messages : [];
        let newMessages = [...threadMessages, ...actionMessages]
            .sort((a, b) => a.created_at - b.created_at)
            .filter(message => !message.hidden);
        setMessages(newMessages);
    }, [thread, actionMessages]);

    const addMessageOptimistically = (messageContent) => {
        const optimisticMessage = {
            content: messageContent,
            role: 'user',
            hidden: false,
            id: `temp-${Date.now()}`,
            created_at: Date.now(),
        };
        setMessages(prevMessages => [...prevMessages, optimisticMessage]);
    };

    const clearThread = () => {
        localStorage.removeItem("thread_id");
        setThreadId(undefined);
        setThread({ messages: [] });
        setRun(undefined);
        setMessages([]);
        setActionMessages([]);
    };

    return { threadId, messages, actionMessages, setActionMessages, clearThread, addMessageOptimistically };
};
