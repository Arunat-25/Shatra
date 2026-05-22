import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { PAGE_TRANSITION_DURATION } from '../constants';

export default function PageTransition({ children }) {
  const location = useLocation();
  const [displayChildren, setDisplayChildren] = useState(children);
  const [transitionStage, setTransitionStage] = useState('enter');
  const prevPathRef = useRef(location.pathname);

  useEffect(() => {
    if (location.pathname !== prevPathRef.current) {
      setTransitionStage('exit');
      const timeout = setTimeout(() => {
        setDisplayChildren(children);
        prevPathRef.current = location.pathname;
        setTransitionStage('enter');
      }, PAGE_TRANSITION_DURATION);
      return () => clearTimeout(timeout);
    } else {
      setDisplayChildren(children);
    }
  }, [children, location.pathname]);

  return (
    <div
      className={`page-transition page-${transitionStage}`}
      style={{
        opacity: transitionStage === 'enter' ? 1 : 0,
        transform: transitionStage === 'enter' ? 'translateY(0)' : 'translateY(10px)',
        transition: `opacity ${PAGE_TRANSITION_DURATION}ms ease-out, transform ${PAGE_TRANSITION_DURATION}ms ease-out`,
        width: '100%',
        height: '100%',
      }}
    >
      {displayChildren}
    </div>
  );
}