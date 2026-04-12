import React, { useEffect, useRef } from 'react';

const InfiniteScroll = ({ loadMore }) => {
    const loaderRef = useRef(null);

    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                loadMore();
            }
        });

        if (loaderRef.current) {
            observer.observe(loaderRef.current);
        }

        // BROKEN: Missing cleanup function!
        // The observer will keep watching the DOM even if 
        // this component is destroyed.
    }, [loadMore]);

    return <div ref={loaderRef}>Loading more posts...</div>;
};

export default InfiniteScroll;