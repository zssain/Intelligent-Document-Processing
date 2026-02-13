import { createFileRoute } from '@tanstack/react-router'
import { Chat } from '@/features/chat'

export const Route = createFileRoute('/chat')({
    component: ChatPage,
})

function ChatPage() {
    return (
        <div className="flex flex-1 overflow-hidden h-full">
            <Chat.View />
            <Chat.Panel />
        </div>
    )
}
