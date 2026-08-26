import * as PopoverPrimitive from '@radix-ui/react-popover'
import * as React from 'react'

import { cn } from '@/lib/utils/ui'

function Popover({
	...props
}: React.ComponentProps<typeof PopoverPrimitive.Root>) {
	return <PopoverPrimitive.Root data-slot="popover" {...props} />
}

function PopoverTrigger({
	...props
}: React.ComponentProps<typeof PopoverPrimitive.Trigger>) {
	return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />
}

function PopoverContent({
	className,
	align = 'center',
	sideOffset = 4,
	container,
	...props
}: React.ComponentProps<typeof PopoverPrimitive.Content> & {
	container?: HTMLElement | null
}) {
	return (
		<PopoverPrimitive.Portal container={container}>
			<PopoverPrimitive.Content
				data-slot="popover-content"
				align={align}
				sideOffset={sideOffset}
				className={cn(
					'bg-popover text-popover-foreground z-50 w-72 rounded-md border p-0 shadow-lg outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95',
					className,
				)}
				{...props}
			/>
		</PopoverPrimitive.Portal>
	)
}

export { Popover, PopoverContent, PopoverTrigger }
