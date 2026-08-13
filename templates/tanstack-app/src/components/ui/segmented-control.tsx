import type { ReactNode } from 'react'

import { cn } from '@/lib/utils/ui'

type SegmentedControlOption<T extends string> = {
	value: T
	label: string
	icon?: ReactNode
}

type SegmentedControlProps<T extends string> = {
	options: SegmentedControlOption<T>[]
	value: T | undefined
	onChange: (value: T) => void
	disabled?: boolean
	className?: string
}

export function SegmentedControl<T extends string>({
	options,
	value,
	onChange,
	disabled = false,
	className,
}: SegmentedControlProps<T>) {
	return (
		<div
			className={cn('bg-muted grid w-full rounded-md p-1 gap-1', className)}
			style={{
				gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))`,
			}}
		>
			{options.map((option) => {
				const isSelected = value === option.value
				return (
					<button
						key={option.value}
						type="button"
						aria-pressed={isSelected}
						disabled={disabled}
						onClick={() => onChange(option.value)}
						className={cn(
							'flex items-center justify-center gap-1.5 rounded-sm px-2 py-2 text-sm font-medium leading-tight transition-all text-balance',
							isSelected
								? 'bg-background text-foreground shadow-sm'
								: 'text-muted-foreground hover:text-foreground',
							disabled && 'pointer-events-none opacity-50',
						)}
					>
						{option.icon}
						{option.label}
					</button>
				)
			})}
		</div>
	)
}
