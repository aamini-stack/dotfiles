import { CheckIcon } from '@phosphor-icons/react'
import { Checkbox as CheckboxPrimitive } from 'radix-ui'
import * as React from 'react'

import { cn } from '@/lib/utils/ui'

function Checkbox({
	className,
	...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
	return (
		<CheckboxPrimitive.Root
			data-slot="checkbox"
			className={cn(
				'peer border-border bg-background data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground size-5 shrink-0 rounded-sm border shadow-xs transition-colors outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-40',
				className,
			)}
			{...props}
		>
			<CheckboxPrimitive.Indicator className="grid place-items-center">
				<CheckIcon className="size-3" weight="bold" />
			</CheckboxPrimitive.Indicator>
		</CheckboxPrimitive.Root>
	)
}

export { Checkbox }
