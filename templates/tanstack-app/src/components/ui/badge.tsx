import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'
import * as React from 'react'

import { cn } from '@/lib/utils/ui'

const badgeVariants = cva(
	"inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-3",
	{
		variants: {
			variant: {
				default: 'border-transparent bg-primary text-primary-foreground',
				secondary: 'border-transparent bg-sky-tint text-primary',
				outline: 'border-border text-foreground',
				muted: 'border-transparent bg-muted text-muted-foreground',
			},
		},
		defaultVariants: {
			variant: 'default',
		},
	},
)

function Badge({
	className,
	variant = 'default',
	asChild = false,
	...props
}: React.ComponentProps<'span'> &
	VariantProps<typeof badgeVariants> & {
		asChild?: boolean
	}) {
	const Comp = asChild ? Slot.Root : 'span'

	return (
		<Comp
			data-slot="badge"
			data-variant={variant}
			className={cn(badgeVariants({ variant, className }))}
			{...props}
		/>
	)
}

export { Badge, badgeVariants }
